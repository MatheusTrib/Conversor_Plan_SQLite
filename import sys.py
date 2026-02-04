import sys
import sqlite3
import pandas as pd
import unicodedata
import re
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QMessageBox, QRadioButton, 
    QGroupBox, QProgressBar, QFrame, QPlainTextEdit, QSizePolicy,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QScrollArea
)
from PySide6.QtCore import Qt, QThread, Signal

class ConversorWorker(QThread):
    progresso = Signal(int)
    status = Signal(str)
    finalizado = Signal(bool, str)

    def __init__(self, excel_path, db_path, modo, df_preview, tipo_mapeamento, colunas_pk, db_existente_path=None):
        super().__init__()
        self.excel_path = excel_path
        self.db_path = db_path
        self.modo = modo
        self.df_preview = df_preview
        self.tipo_mapeamento = tipo_mapeamento
        self.colunas_pk = colunas_pk
        self.db_existente_path = db_existente_path  # Caminho do banco existente para append

    def obter_estrutura_tabela_existente(self, conn, nome_tabela):
        """Obtém a estrutura (colunas e tipos) de uma tabela existente"""
        try:
            cursor = conn.cursor()
            cursor.execute(f'PRAGMA table_info("{nome_tabela}")')
            colunas_info = cursor.fetchall()
            
            # Retorna dicionário {nome_coluna: tipo}
            estrutura = {col[1]: col[2] for col in colunas_info}
            
            # Identifica colunas da PK (todas exceto _PK)
            tem_pk = '_PK' in estrutura
            colunas_dados = [col for col in estrutura.keys() if col != '_PK']
            
            return estrutura, tem_pk, colunas_dados
        except:
            return None, False, []
    
    def salvar_metadata_pk(self, conn, tabela, colunas_pk):
        """Salva informação sobre quais colunas formam a PK de uma tabela"""
        if not colunas_pk or len(colunas_pk) == 0:
            return
        
        cursor = conn.cursor()
        colunas_str = ','.join(colunas_pk)
        
        cursor.execute("""
            INSERT OR REPLACE INTO _dataforge_metadata (tabela, colunas_pk, data_criacao)
            VALUES (?, ?, datetime('now'))
        """, (tabela, colunas_str))
        conn.commit()
    
    def obter_metadata_pk(self, conn, tabela):
        """Recupera quais colunas formam a PK de uma tabela"""
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT colunas_pk FROM _dataforge_metadata WHERE tabela = ?
            """, (tabela,))
            
            resultado = cursor.fetchone()
            if resultado and resultado[0]:
                return resultado[0].split(',')
            return None
        except:
            return None
    
    def criar_coluna_pk(self, df, colunas_pk):
        """Cria coluna _PK concatenando as colunas selecionadas"""
        if not colunas_pk or len(colunas_pk) == 0:
            return df, None
        
        # Concatena as colunas escolhidas com separador '|'
        df['_PK'] = df[colunas_pk].astype(str).agg('|'.join, axis=1)
        return df, '_PK'
    
    def verificar_duplicatas(self, conn, nome_tabela, df, coluna_pk):
        """Verifica quais registros já existem na tabela baseado na PK"""
        if not coluna_pk:
            return df, 0
        
        try:
            # Verifica se a tabela existe
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{nome_tabela}'")
            if not cursor.fetchone():
                return df, 0  # Tabela não existe, insere tudo
            
            # Busca PKs já existentes
            pks_existentes = pd.read_sql(f'SELECT {coluna_pk} FROM "{nome_tabela}"', conn)
            pks_existentes_set = set(pks_existentes[coluna_pk].tolist())
            
            # Filtra apenas os novos
            df_original_len = len(df)
            df_novo = df[~df[coluna_pk].isin(pks_existentes_set)]
            duplicatas = df_original_len - len(df_novo)
            
            return df_novo, duplicatas
        except Exception as e:
            self.status.emit(f"⚠ Aviso ao verificar duplicatas: {str(e)}")
            return df, 0
    
    def criar_schema_sql(self, df, nome_tabela, tipos):
        """Cria a tabela com os tipos definidos pelo usuário"""
        colunas_sql = []
        for col in df.columns:
            tipo_usuario = tipos.get(col, 'TEXT')
            colunas_sql.append(f'"{col}" {tipo_usuario}')
        
        schema = f'CREATE TABLE IF NOT EXISTS "{nome_tabela}" ({", ".join(colunas_sql)})'
        return schema
    
    def converter_tipos_python_para_sqlite(self, df):
        """Converte tipos Python incompatíveis para tipos que o SQLite aceita"""
        df_convertido = df.copy()
        
        for col in df_convertido.columns:
            # Converte Timestamp/datetime para string ISO
            if pd.api.types.is_datetime64_any_dtype(df_convertido[col]):
                df_convertido[col] = df_convertido[col].astype(str)
            
            # Converte timedelta para string
            elif pd.api.types.is_timedelta64_dtype(df_convertido[col]):
                df_convertido[col] = df_convertido[col].astype(str)
            
            # Converte objetos complexos para string
            elif df_convertido[col].dtype == 'object':
                df_convertido[col] = df_convertido[col].apply(
                    lambda x: str(x) if pd.notna(x) and not isinstance(x, (str, int, float)) else x
                )
        
        return df_convertido
    
    def converter_coluna_tipo(self, df, col_name, tipo_escolhido):
        """Converte uma coluna para o tipo especificado"""
        if tipo_escolhido == 'INTEGER':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0).astype(int)
        elif tipo_escolhido == 'REAL':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        elif tipo_escolhido == 'BOOLEAN':
            df[col_name] = df[col_name].map({'true': 1, 'false': 0, '1': 1, '0': 0, 'sim': 1, 'não': 0, 'yes': 1, 'no': 0})
        # TEXT, DATE, DATETIME, TIME, NUMERIC e BLOB permanecem como string
        return df

    def run(self):
        try:
            self.status.emit("Iniciando leitura ultra-rápida...")
            
            # Determina o engine baseado na extensão
            ext = Path(self.excel_path).suffix.lower()
            if ext == '.csv':
                # Para CSV, lê diretamente TUDO COMO STRING
                abas_dict = {'Sheet1': pd.read_csv(self.excel_path, dtype=str, keep_default_na=False)}
                abas = list(abas_dict.keys())
            elif ext in ['.xlsx', '.xls', '.xlsm']:
                xls = pd.ExcelFile(self.excel_path, engine='calamine' if ext == '.xlsx' else 'xlrd')
                abas = xls.sheet_names
                # Lê TUDO COMO STRING para preservar formato original
                abas_dict = {aba: pd.read_excel(xls, sheet_name=aba, dtype=str, keep_default_na=False) for aba in abas}
            else:
                raise ValueError(f"Formato não suportado: {ext}")
            
            # Define o caminho do banco baseado no modo
            if self.modo == 'append' and self.db_existente_path:
                db_final = self.db_existente_path
                self.status.emit(f"Conectando ao banco existente: {db_final}")
            else:
                db_final = self.db_path
            
            conn = sqlite3.connect(db_final)
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("PRAGMA journal_mode = MEMORY")
            cursor = conn.cursor()
            
            # Cria tabela de metadados se não existir (armazena info sobre PKs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _dataforge_metadata (
                    tabela TEXT PRIMARY KEY,
                    colunas_pk TEXT,
                    data_criacao TEXT
                )
            """)
            conn.commit()
            
            for i, aba in enumerate(abas):
                self.status.emit(f"Processando aba: {aba}")
                df = abas_dict[aba]
                
                # Aplica a normalização de colunas conforme preview
                colunas_originais = df.columns.tolist()
                df.columns = [self.normalizar_nome_coluna(col) for col in df.columns]
                
                # Se modo for APPEND, usa a estrutura do banco existente
                if self.modo == 'append':
                    estrutura_existente, tem_pk_existente, colunas_existentes = self.obter_estrutura_tabela_existente(conn, aba)
                    
                    if estrutura_existente:
                        self.status.emit(f"✓ Usando estrutura existente da tabela '{aba}'")
                        
                        # Se tem PK existente, recupera metadados para saber quais colunas formam a PK
                        if tem_pk_existente:
                            colunas_pk_metadata = self.obter_metadata_pk(conn, aba)
                            
                            if colunas_pk_metadata:
                                # Usa as colunas armazenadas nos metadados
                                # Verifica se todas as colunas existem no novo arquivo
                                colunas_pk_validas = [col for col in colunas_pk_metadata if col in df.columns]
                                
                                if len(colunas_pk_validas) == len(colunas_pk_metadata):
                                    df, coluna_pk = self.criar_coluna_pk(df, colunas_pk_validas)
                                    self.status.emit(f"  🔑 PK reconstruída: {' + '.join(colunas_pk_validas)}")
                                else:
                                    # Faltam colunas
                                    faltantes = set(colunas_pk_metadata) - set(colunas_pk_validas)
                                    self.status.emit(f"  ⚠ ERRO: Arquivo não possui colunas da PK: {', '.join(faltantes)}")
                                    self.status.emit(f"  ⚠ Tabela '{aba}' será ignorada")
                                    continue
                            else:
                                # Metadados não encontrados - banco antigo sem metadata
                                self.status.emit(f"  ⚠ Metadados de PK não encontrados para '{aba}'")
                                self.status.emit(f"  ⚠ Não é possível verificar duplicatas - insere tudo")
                                coluna_pk = None
                        else:
                            coluna_pk = None
                            self.status.emit(f"  ℹ Tabela não possui _PK - duplicatas não serão verificadas")
                        
                        # Ajusta colunas do DataFrame para bater com as existentes
                        # Remove colunas que não existem no banco
                        colunas_df = [col for col in df.columns if col in estrutura_existente or col == '_PK']
                        df = df[colunas_df]
                        
                        # Adiciona colunas que faltam (preenchendo com None)
                        for col_existente in estrutura_existente.keys():
                            if col_existente not in df.columns and col_existente != '_PK':
                                df[col_existente] = None
                        
                        # Reordena colunas para bater com a estrutura do banco
                        ordem_colunas = list(estrutura_existente.keys())
                        df = df[ordem_colunas]
                        
                        # Não aplica conversão de tipos - usa a estrutura existente
                        tipos_aba = estrutura_existente
                    else:
                        # Tabela não existe no banco, cria nova
                        self.status.emit(f"⚠ Tabela '{aba}' não existe no banco - será criada")
                        colunas_pk_aba = self.colunas_pk.get(aba, [])
                        df, coluna_pk = self.criar_coluna_pk(df, colunas_pk_aba)
                        tipos_aba = self.tipo_mapeamento.get(aba, {})
                        
                        # Aplica conversão de tipos
                        for col_name in df.columns:
                            if col_name == '_PK':
                                continue
                            tipo_escolhido = tipos_aba.get(col_name, 'TEXT')
                            df = self.converter_coluna_tipo(df, col_name, tipo_escolhido)
                else:
                    # Modo REPLACE - usa parametrização do usuário
                    colunas_pk_aba = self.colunas_pk.get(aba, [])
                    df, coluna_pk = self.criar_coluna_pk(df, colunas_pk_aba)
                    tipos_aba = self.tipo_mapeamento.get(aba, {})
                    
                    # Aplica conversão de tipos
                    for col_name in df.columns:
                        if col_name == '_PK':
                            continue
                        tipo_escolhido = tipos_aba.get(col_name, 'TEXT')
                        df = self.converter_coluna_tipo(df, col_name, tipo_escolhido)
                
                # Converte tipos Python incompatíveis para SQLite (datas, etc)
                df = self.converter_tipos_python_para_sqlite(df)
                
                # Se modo for replace, drop a tabela primeiro
                if self.modo == 'replace':
                    cursor.execute(f'DROP TABLE IF EXISTS "{aba}"')
                    # Cria tabela com schema customizado
                    tipos_com_pk = tipos_aba.copy()
                    if coluna_pk:
                        tipos_com_pk['_PK'] = 'TEXT'
                        # Salva metadados sobre quais colunas formam a PK
                        self.salvar_metadata_pk(conn, aba, colunas_pk_aba)
                    schema = self.criar_schema_sql(df, aba, tipos_com_pk)
                    cursor.execute(schema)
                    duplicatas_ignoradas = 0
                else:
                    # Modo append: verifica duplicatas
                    df, duplicatas_ignoradas = self.verificar_duplicatas(conn, aba, df, coluna_pk)
                    
                    if duplicatas_ignoradas > 0:
                        self.status.emit(f"⚠ {duplicatas_ignoradas} registros duplicados ignorados em '{aba}'")
                    
                    # Garante que a tabela existe (caso seja nova tabela)
                    if not estrutura_existente:
                        tipos_com_pk = tipos_aba.copy()
                        if coluna_pk:
                            tipos_com_pk['_PK'] = 'TEXT'
                            # Salva metadados para nova tabela criada no modo append
                            colunas_pk_aba = self.colunas_pk.get(aba, [])
                            self.salvar_metadata_pk(conn, aba, colunas_pk_aba)
                        schema = self.criar_schema_sql(df, aba, tipos_com_pk)
                        try:
                            cursor.execute(schema)
                        except:
                            pass  # Tabela já existe
                
                # Insere apenas os dados novos (não duplicados)
                if len(df) > 0:
                    placeholders = ', '.join(['?' for _ in df.columns])
                    insert_sql = f'INSERT INTO "{aba}" VALUES ({placeholders})'
                    
                    dados = [tuple(row) for row in df.values]
                    cursor.executemany(insert_sql, dados)
                    self.status.emit(f"✓ {len(df)} registros inseridos em '{aba}'")
                else:
                    self.status.emit(f"⚠ Nenhum registro novo para inserir em '{aba}'")
                
                self.progresso.emit(int(((i + 1) / len(abas)) * 100))

            conn.commit()
            conn.close()
            self.finalizado.emit(True, "Processo concluído com sucesso!")
        except Exception as e:
            self.finalizado.emit(False, str(e))

    def normalizar_nome_coluna(self, nome):
        """Normaliza nome da coluna removendo acentos e substituindo espaços"""
        # Remove acentuação
        nome_normalizado = unicodedata.normalize('NFKD', str(nome))
        nome_normalizado = nome_normalizado.encode('ASCII', 'ignore').decode('ASCII')
        
        # Substitui espaços por underscore
        nome_normalizado = re.sub(r'\s+', '_', nome_normalizado)
        
        # Remove caracteres especiais que não sejam letras, números ou underscore
        nome_normalizado = re.sub(r'[^a-zA-Z0-9_]', '', nome_normalizado)
        
        return nome_normalizado


class ResponsiveConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataForge Pro")
        self.setMinimumSize(800, 700)
        self.excel_path = None
        self.db_path_existente = None  # Para modo append
        self.preview_data = None
        self.tipo_combos = {}  # Armazena os comboboxes de tipo
        self.pk_checkboxes = {}  # Armazena os checkboxes de PK
        self.init_ui()

    def init_ui(self):
        # Layout Principal com margens generosas
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(15)

        # --- Cabeçalho ---
        header_layout = QVBoxLayout()
        self.lbl_titulo = QLabel("Conversor de Dados")
        self.lbl_titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #BB86FC;")
        
        self.lbl_subtitulo = QLabel("XLSX/CSV/XLS para SQLite Engine")
        self.lbl_subtitulo.setStyleSheet("color: #9E9E9E; font-size: 14px;")
        
        header_layout.addWidget(self.lbl_titulo)
        header_layout.addWidget(self.lbl_subtitulo)
        main_layout.addLayout(header_layout)

        # --- Card de Seleção (Responsivo) ---
        self.card_file = QFrame()
        self.card_file.setObjectName("card")
        self.card_file.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        card_layout = QVBoxLayout(self.card_file)
        
        # Layout horizontal para botões de ação
        btn_layout = QHBoxLayout()
        
        self.btn_excel = QPushButton("📁 Selecionar Arquivo")
        self.btn_excel.setCursor(Qt.PointingHandCursor)
        self.btn_excel.clicked.connect(self.selecionar_excel)
        
        self.btn_guia = QPushButton("📖 Baixar Guia de Tipos")
        self.btn_guia.setCursor(Qt.PointingHandCursor)
        self.btn_guia.clicked.connect(self.baixar_guia_tipos)
        
        btn_layout.addWidget(self.btn_excel)
        btn_layout.addWidget(self.btn_guia)
        
        self.lbl_info = QLabel("Nenhum arquivo selecionado")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setAlignment(Qt.AlignCenter)

        card_layout.addLayout(btn_layout)
        card_layout.addWidget(self.lbl_info)
        main_layout.addWidget(self.card_file)

        # --- Preview de Dados (Tabela com tipos) ---
        self.preview_group = QGroupBox("Preview dos Dados e Tipos")
        self.preview_group.setVisible(False)
        preview_layout = QVBoxLayout(self.preview_group)
        
        # Scroll area para a tabela
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)
        
        self.preview_table = QTableWidget()
        self.preview_table.setObjectName("preview_table")
        scroll.setWidget(self.preview_table)
        
        preview_layout.addWidget(scroll)
        main_layout.addWidget(self.preview_group)

        # --- Opções (Lado a Lado se houver espaço) ---
        self.opts_group = QGroupBox("Modo de Gravação")
        opts_layout = QVBoxLayout(self.opts_group)
        
        # Radio buttons
        radio_layout = QHBoxLayout()
        self.radio_novo = QRadioButton("Novo Banco (.db)")
        self.radio_append = QRadioButton("Anexar a Banco Existente")
        self.radio_novo.setChecked(True)
        
        radio_layout.addWidget(self.radio_novo)
        radio_layout.addWidget(self.radio_append)
        opts_layout.addLayout(radio_layout)
        
        # Frame para seleção de banco existente (inicialmente oculto)
        self.frame_db_existente = QFrame()
        self.frame_db_existente.setObjectName("card")
        self.frame_db_existente.setVisible(False)
        
        db_existente_layout = QHBoxLayout(self.frame_db_existente)
        self.btn_selecionar_db = QPushButton("📂 Selecionar Banco Existente")
        self.btn_selecionar_db.setCursor(Qt.PointingHandCursor)
        self.btn_selecionar_db.clicked.connect(self.selecionar_banco_existente)
        
        self.lbl_db_selecionado = QLabel("Nenhum banco selecionado")
        self.lbl_db_selecionado.setWordWrap(True)
        
        db_existente_layout.addWidget(self.btn_selecionar_db)
        db_existente_layout.addWidget(self.lbl_db_selecionado, 1)
        
        opts_layout.addWidget(self.frame_db_existente)
        
        # Conecta mudança de radio button
        self.radio_novo.toggled.connect(self.atualizar_modo_gravacao)
        self.radio_append.toggled.connect(self.atualizar_modo_gravacao)
        
        main_layout.addWidget(self.opts_group)

        # --- Console de Log ---
        self.log_console = QPlainTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setPlaceholderText("Logs do sistema aparecerão aqui...")
        self.log_console.setObjectName("console")
        self.log_console.setMaximumHeight(150)
        main_layout.addWidget(self.log_console)

        # --- Footer (Progresso e Ação) ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.btn_run = QPushButton("EXECUTAR CONVERSÃO")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setMinimumHeight(50)

        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.btn_run)
        
        self.btn_run.clicked.connect(self.executar)
        self.aplicar_estilo()

    def aplicar_estilo(self):
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #E0E0E0; font-family: 'Segoe UI'; }
            #card { 
                background-color: #1E1E1E; 
                border-radius: 12px; 
                padding: 20px; 
                border: 1px solid #333;
            }
            #console {
                background-color: #000000;
                border: 1px solid #333;
                border-radius: 6px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
                color: #00FF41;
            }
            #preview_table {
                background-color: #1E1E1E;
                border: 1px solid #333;
                gridline-color: #333;
            }
            #preview_table::item {
                padding: 5px;
            }
            QPushButton {
                background-color: #333;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                border: 1px solid #444;
            }
            QPushButton:hover { background-color: #444; border: 1px solid #BB86FC; }
            #btn_run {
                background-color: #BB86FC;
                color: #000;
                font-size: 16px;
            }
            #btn_run:hover { background-color: #D7B7FD; }
            QProgressBar {
                border: 2px solid #333;
                border-radius: 10px;
                text-align: center;
                background: #1E1E1E;
            }
            QProgressBar::chunk { background-color: #03DAC6; border-radius: 8px; }
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #333; 
                border-radius: 8px; 
                margin-top: 10px; 
                padding: 10px;
            }
            QComboBox {
                background-color: #2A2A2A;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
                color: #E0E0E0;
            }
            QComboBox:hover {
                border: 1px solid #BB86FC;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #2A2A2A;
                selection-background-color: #BB86FC;
                selection-color: #000;
            }
        """)

    def log(self, texto):
        self.log_console.appendPlainText(f"> {texto}")

    def normalizar_nome_coluna(self, nome):
        """Normaliza nome da coluna removendo acentos e substituindo espaços"""
        nome_original = nome
        # Remove acentuação
        nome_normalizado = unicodedata.normalize('NFKD', str(nome))
        nome_normalizado = nome_normalizado.encode('ASCII', 'ignore').decode('ASCII')
        
        # Substitui espaços por underscore
        nome_normalizado = re.sub(r'\s+', '_', nome_normalizado)
        
        # Remove caracteres especiais que não sejam letras, números ou underscore
        nome_normalizado = re.sub(r'[^a-zA-Z0-9_]', '', nome_normalizado)
        
        if nome_original != nome_normalizado:
            self.log(f"Coluna normalizada: '{nome_original}' → '{nome_normalizado}'")
        
        return nome_normalizado

    def detectar_tipo_coluna(self, series):
        """Detecta automaticamente o tipo de dado da coluna (dados lidos como string)"""
        # Remove valores vazios para análise
        series_limpa = series[series != ''].dropna()
        
        if len(series_limpa) == 0:
            return 'TEXT'
        
        # Pega amostra para teste
        amostra = series_limpa.head(min(100, len(series_limpa)))
        
        # Tenta detectar INTEGER
        try:
            valores_numericos = pd.to_numeric(amostra, errors='raise')
            # Verifica se todos são inteiros
            if all(float(v).is_integer() for v in valores_numericos if pd.notna(v)):
                return 'INTEGER'
            else:
                return 'REAL'
        except (ValueError, TypeError):
            pass
        
        # Tenta detectar datas
        try:
            pd.to_datetime(amostra, errors='raise')
            # Verifica se tem informação de hora analisando a string
            sample_str = str(amostra.iloc[0])
            if any(char in sample_str for char in [':', 'T']) or len(sample_str) > 10:
                return 'DATETIME'
            else:
                return 'DATE'
        except (ValueError, TypeError):
            pass
        
        # Verifica se parece booleano
        valores_unicos = set(str(v).lower() for v in amostra.unique())
        if valores_unicos.issubset({'true', 'false', '1', '0', 'yes', 'no', 'sim', 'não', 'verdadeiro', 'falso'}):
            return 'BOOLEAN'
        
        # Por padrão, mantém como TEXT (preserva tudo, incluindo IDs longos)
        return 'TEXT'

    def carregar_preview(self, filepath):
        """Carrega preview do arquivo com detecção de tipos"""
        try:
            ext = Path(filepath).suffix.lower()
            
            # Lê apenas as primeiras linhas para preview - TUDO COMO STRING
            if ext == '.csv':
                df = pd.read_csv(filepath, nrows=100, dtype=str, keep_default_na=False)
                sheet_name = 'Sheet1'
            elif ext in ['.xlsx', '.xls', '.xlsm']:
                xls = pd.ExcelFile(filepath, engine='calamine' if ext == '.xlsx' else 'xlrd')
                sheet_name = xls.sheet_names[0]  # Pega primeira aba
                df = pd.read_excel(xls, sheet_name=sheet_name, nrows=100, dtype=str, keep_default_na=False)
            else:
                raise ValueError(f"Formato não suportado: {ext}")
            
            self.preview_data = {sheet_name: df}
            self.mostrar_preview(df, sheet_name)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar preview: {str(e)}")
            self.log(f"❌ Erro no preview: {str(e)}")

    def mostrar_preview(self, df, sheet_name):
        """Mostra a tabela de preview com combos de tipos e checkboxes de PK"""
        from PySide6.QtWidgets import QCheckBox
        
        self.preview_group.setVisible(True)
        
        # Normaliza nomes das colunas
        colunas_originais = df.columns.tolist()
        colunas_normalizadas = [self.normalizar_nome_coluna(col) for col in colunas_originais]
        
        # Configura tabela: 2 linhas de header (tipo + PK) + 1 linha info + 4 linhas de dados
        self.preview_table.setRowCount(7)
        self.preview_table.setColumnCount(len(colunas_normalizadas))
        
        # Define headers
        self.preview_table.setHorizontalHeaderLabels(colunas_normalizadas)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        # Primeira linha: ComboBox de tipos
        tipos_sql = ['TEXT', 'INTEGER', 'REAL', 'NUMERIC', 'BLOB', 'DATE', 'DATETIME', 'TIME', 'BOOLEAN']
        self.tipo_combos[sheet_name] = {}
        self.pk_checkboxes[sheet_name] = {}
        
        for col_idx, col_name in enumerate(colunas_normalizadas):
            # ComboBox de tipo
            combo = QComboBox()
            combo.addItems(tipos_sql)
            
            # Detecta tipo automaticamente
            tipo_detectado = self.detectar_tipo_coluna(df[colunas_originais[col_idx]])
            combo.setCurrentText(tipo_detectado)
            
            self.preview_table.setCellWidget(0, col_idx, combo)
            self.tipo_combos[sheet_name][col_name] = combo
            
            # Checkbox para chave primária (linha 2)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox::indicator { width: 18px; height: 18px; }")
            checkbox_layout.addWidget(checkbox)
            
            self.preview_table.setCellWidget(1, col_idx, checkbox_widget)
            self.pk_checkboxes[sheet_name][col_name] = checkbox
        
        # Labels de linha
        labels = ['Tipo →', 'Chave PK ✓', '', 'Linha 1', 'Linha 2', 'Linha 3', 'Linha 4']
        self.preview_table.setVerticalHeaderLabels(labels)
        
        # Linha explicativa (linha 3)
        info_item = QTableWidgetItem("← Marque as colunas que formam a chave única para evitar duplicatas (ex: N_Documento + Material)")
        info_item.setFlags(info_item.flags() & ~Qt.ItemIsEditable)
        info_item.setForeground(Qt.gray)
        self.preview_table.setItem(2, 0, info_item)
        self.preview_table.setSpan(2, 0, 1, len(colunas_normalizadas))  # Mescla todas as colunas
        
        # Preenche dados de exemplo (4 primeiras linhas)
        for row_idx in range(min(4, len(df))):
            for col_idx in range(len(colunas_normalizadas)):
                valor = str(df.iloc[row_idx, col_idx])
                item = QTableWidgetItem(valor)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.preview_table.setItem(row_idx + 3, col_idx, item)
        
        self.log(f"✓ Preview carregado: {len(colunas_normalizadas)} colunas detectadas")

    def atualizar_modo_gravacao(self):
        """Atualiza a interface baseado no modo selecionado"""
        if self.radio_append.isChecked():
            self.frame_db_existente.setVisible(True)
            self.log("ℹ Modo 'Anexar' selecionado - Selecione o banco existente")
        else:
            self.frame_db_existente.setVisible(False)
            self.db_path_existente = None
            self.lbl_db_selecionado.setText("Nenhum banco selecionado")
    
    def selecionar_banco_existente(self):
        """Abre diálogo para selecionar banco SQLite existente"""
        db_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Banco de Dados Existente",
            "",
            "Banco SQLite (*.db *.sqlite *.sqlite3)"
        )
        
        if db_path:
            self.db_path_existente = Path(db_path)
            self.lbl_db_selecionado.setText(f"✓ {self.db_path_existente.name}")
            self.log(f"Banco selecionado: {db_path}")
            
            # Analisa a estrutura do banco existente
            self.analisar_banco_existente()
    
    def analisar_banco_existente(self):
        """Analisa o banco existente e extrai estrutura de colunas e tipos"""
        try:
            conn = sqlite3.connect(self.db_path_existente)
            cursor = conn.cursor()
            
            # Lista todas as tabelas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tabelas = [row[0] for row in cursor.fetchall() if row[0] != '_dataforge_metadata']
            
            if not tabelas:
                self.log("⚠ Banco vazio - nenhuma tabela encontrada")
                conn.close()
                return
            
            self.log(f"📊 Banco contém {len(tabelas)} tabela(s): {', '.join(tabelas)}")
            
            # Para cada tabela, busca a estrutura
            for tabela in tabelas:
                cursor.execute(f'PRAGMA table_info("{tabela}")')
                colunas_info = cursor.fetchall()
                
                colunas_str = ", ".join([f"{col[1]} ({col[2]})" for col in colunas_info])
                self.log(f"  • {tabela}: {colunas_str}")
                
                # Verifica se tem coluna _PK
                tem_pk = any(col[1] == '_PK' for col in colunas_info)
                if tem_pk:
                    # Busca metadados da PK
                    try:
                        cursor.execute("SELECT colunas_pk FROM _dataforge_metadata WHERE tabela = ?", (tabela,))
                        metadata = cursor.fetchone()
                        if metadata and metadata[0]:
                            colunas_pk = metadata[0].split(',')
                            self.log(f"    🔑 PK formada por: {' + '.join(colunas_pk)}")
                        else:
                            self.log(f"    🔑 Possui coluna _PK (metadados não disponíveis)")
                    except:
                        self.log(f"    🔑 Possui coluna _PK (metadados não disponíveis)")
            
            conn.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao analisar banco: {str(e)}")
            self.log(f"❌ Erro ao analisar banco: {str(e)}")

    def selecionar_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Selecionar Arquivo", 
            "", 
            "Arquivos Suportados (*.xlsx *.xls *.csv *.xlsm);;Excel (*.xlsx *.xls *.xlsm);;CSV (*.csv)"
        )
        if path:
            self.excel_path = Path(path)
            self.lbl_info.setText(f"Arquivo Pronto: {self.excel_path.name}")
            self.log(f"Arquivo carregado: {path}")
            self.carregar_preview(path)

    def baixar_guia_tipos(self):
        """Cria e salva um guia de tipos de dados SQLite"""
        guia_conteudo = """
===========================================
   GUIA DE TIPOS DE DADOS SQLITE
===========================================

SQLite utiliza um sistema de tipos dinâmico. Os principais tipos são:

1. TEXT
   - Armazena texto (strings)
   - Exemplos: nomes, descrições, endereços
   - Uso: "João Silva", "Rua ABC, 123"

2. INTEGER
   - Números inteiros (sem casas decimais)
   - Exemplos: idades, quantidades, IDs
   - Uso: 25, 100, -5

3. REAL
   - Números com ponto flutuante (decimais)
   - Exemplos: preços, médias, percentuais
   - Uso: 19.99, 3.14159, 75.5

4. NUMERIC
   - Tipo genérico que pode armazenar INTEGER, REAL ou TEXT
   - SQLite escolhe automaticamente baseado no valor
   - Uso: quando o tipo pode variar

5. BLOB
   - Dados binários (Binary Large Object)
   - Exemplos: imagens, arquivos
   - Uso: dados não-textuais armazenados como estão

6. DATE
   - Datas sem informação de hora
   - SQLite armazena como TEXT no formato ISO8601
   - Exemplos: "2024-12-25", "2023-01-15"
   - Uso: datas de nascimento, datas de vencimento

7. DATETIME
   - Data e hora combinadas
   - SQLite armazena como TEXT no formato ISO8601
   - Exemplos: "2024-12-25 14:30:00", "2023-01-15T10:45:30"
   - Uso: timestamps, registros de eventos

8. TIME
   - Apenas hora, sem data
   - SQLite armazena como TEXT
   - Exemplos: "14:30:00", "09:15:45"
   - Uso: horários de atendimento, durações

9. BOOLEAN
   - Valores verdadeiro/falso
   - SQLite armazena como INTEGER (0 = false, 1 = true)
   - Exemplos: 0, 1, true, false
   - Uso: flags, indicadores sim/não

===========================================
DICAS IMPORTANTES:
===========================================
- Use TEXT para qualquer dado textual
- Use INTEGER para contagens e IDs
- Use REAL para valores monetários e medições
- Use DATE/DATETIME para datas (serão convertidas para texto ISO)
- Use BOOLEAN para valores sim/não
- Em caso de dúvida, TEXT é sempre seguro
- SQLite é flexível: mesmo declarando um tipo,
  você pode armazenar outros (tipagem dinâmica)

===========================================
CONVERSÃO AUTOMÁTICA:
===========================================
O DataForge Pro converte automaticamente:
- Datas do Excel/Pandas → TEXT (formato ISO8601)
- Timestamps → TEXT (formato ISO8601)
- Objetos complexos → TEXT (string)

Isso evita erros de tipo durante a importação!

===========================================
DataForge Pro - Conversão Inteligente
===========================================
"""
        
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Guia de Tipos",
            "Guia_Tipos_SQLite.txt",
            "Arquivo de Texto (*.txt)"
        )
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(guia_conteudo)
                QMessageBox.information(self, "Sucesso", f"Guia salvo em:\n{save_path}")
                self.log(f"✓ Guia de tipos salvo: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar guia: {str(e)}")

    def executar(self):
        if not self.excel_path:
            return QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
        
        if not self.preview_data:
            return QMessageBox.warning(self, "Aviso", "Preview não carregado.")
        
        modo = "replace" if self.radio_novo.isChecked() else "append"
        
        # Valida seleção de banco no modo append
        if modo == "append" and not self.db_path_existente:
            return QMessageBox.warning(self, "Aviso", "Selecione o banco de dados existente para anexar os dados.")
        
        # Define o caminho do banco
        if modo == "append":
            db_path = self.db_path_existente
        else:
            db_path = self.excel_path.parent / f"{self.excel_path.stem}.db"
        
        # Coleta os tipos definidos pelo usuário
        tipo_mapeamento = {}
        for sheet_name, combos in self.tipo_combos.items():
            tipo_mapeamento[sheet_name] = {
                col_name: combo.currentText() 
                for col_name, combo in combos.items()
            }
        
        # Coleta as colunas marcadas como chave primária
        colunas_pk = {}
        for sheet_name, checkboxes in self.pk_checkboxes.items():
            colunas_selecionadas = [
                col_name for col_name, checkbox in checkboxes.items() 
                if checkbox.isChecked()
            ]
            if colunas_selecionadas:
                colunas_pk[sheet_name] = colunas_selecionadas
                if modo == "replace":  # Só loga para novo banco
                    self.log(f"🔑 Chave primária definida para '{sheet_name}': {' + '.join(colunas_selecionadas)}")
            else:
                colunas_pk[sheet_name] = []
                if modo == "replace":
                    self.log(f"ℹ Nenhuma chave primária definida para '{sheet_name}'")
        
        # No modo append, avisa que parametrização será ignorada
        if modo == "append":
            self.log("ℹ Modo ANEXAR: Usando estrutura do banco existente")
            self.log("ℹ Parametrizações de tipo e PK serão ignoradas")
        
        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Passa o caminho do banco existente se for modo append
        db_existente = self.db_path_existente if modo == "append" else None
        
        self.worker = ConversorWorker(
            self.excel_path, 
            db_path, 
            modo, 
            self.preview_data, 
            tipo_mapeamento, 
            colunas_pk,
            db_existente
        )
        self.worker.status.connect(self.log)
        self.worker.progresso.connect(self.progress_bar.setValue)
        self.worker.finalizado.connect(self.concluir)
        self.worker.start()

    def concluir(self, sucesso, msg):
        self.btn_run.setEnabled(True)
        if sucesso:
            self.log("✓ Operação finalizada com sucesso.")
            QMessageBox.information(self, "Sucesso", msg)
            # Reseta a interface para permitir novo processo
            self.resetar_interface()
        else:
            self.log(f"❌ ERRO: {msg}")
            QMessageBox.critical(self, "Erro", msg)
    
    def resetar_interface(self):
        """Reseta a interface para o estado inicial"""
        self.excel_path = None
        self.db_path_existente = None
        self.preview_data = None
        self.tipo_combos = {}
        self.pk_checkboxes = {}
        
        # Limpa informações do arquivo
        self.lbl_info.setText("Nenhum arquivo selecionado")
        self.lbl_db_selecionado.setText("Nenhum banco selecionado")
        
        # Esconde e limpa o preview
        self.preview_group.setVisible(False)
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        
        # Esconde frame de banco existente
        self.frame_db_existente.setVisible(False)
        
        # Esconde a barra de progresso
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
        # Reseta opções para padrão
        self.radio_novo.setChecked(True)
        
        self.log("🔄 Interface resetada - Pronto para novo arquivo")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ResponsiveConverter()
    win.show()
    sys.exit(app.exec())