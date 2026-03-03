"""
DataForge Pro v2.0 - VERSÃO FINAL INTEGRADA
Conversor Universal: Excel/CSV/NFe/CTe → SQLite

INSTRUÇÕES DE USO:
1. Coloque este arquivo na mesma pasta que xml_processor.py
2. Execute: python dataforge_pro_final.py
3. Use normalmente - interface detecta automaticamente XMLs

CHANGELOG v2.0:
- ✅ Mantém 100% das funcionalidades originais (Excel/CSV)
- ✅ Adiciona suporte completo a NFe e CTe
- ✅ Interface com alternância Planilhas/XMLs
- ✅ Preview em abas para XMLs
- ✅ Export XLSX e Converter SQLite
"""

import sys
import sqlite3
import pandas as pd
import unicodedata
import re
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout,QCheckBox, QMessageBox, QRadioButton, 
    QGroupBox, QProgressBar, QFrame, QPlainTextEdit, QSizePolicy,
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QScrollArea,
    QTabWidget  # Para abas XML
)
from PySide6.QtCore import Qt, QThread, Signal

# Import XML (opcional - funciona sem)
try:
    from xml_processor import XMLProcessor
    XML_SUPPORT = True
except ImportError:
    XML_SUPPORT = False


# ============================================================================
#  WORKERS - THREADS DE PROCESSAMENTO
# ============================================================================

class ConversorWorker(QThread):
    """Thread para processar Excel/CSV - CÓDIGO ORIGINAL MANTIDO 100%"""
    
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
        self.db_existente_path = db_existente_path

    def obter_estrutura_tabela_existente(self, conn, nome_tabela):
        try:
            cursor = conn.cursor()
            cursor.execute(f'PRAGMA table_info("{nome_tabela}")')
            colunas_info = cursor.fetchall()
            estrutura = {col[1]: col[2] for col in colunas_info}
            tem_pk = '_PK' in estrutura
            colunas_dados = [col for col in estrutura.keys() if col != '_PK']
            return estrutura, tem_pk, colunas_dados
        except:
            return None, False, []
    
    def salvar_metadata_pk(self, conn, tabela, colunas_pk):
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
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT colunas_pk FROM _dataforge_metadata WHERE tabela = ?", (tabela,))
            resultado = cursor.fetchone()
            if resultado and resultado[0]:
                return resultado[0].split(',')
            return None
        except:
            return None
    
    def criar_coluna_pk(self, df, colunas_pk):
        if not colunas_pk or len(colunas_pk) == 0:
            return df, None
        df['_PK'] = df[colunas_pk].astype(str).agg('|'.join, axis=1)
        return df, '_PK'
    
    def verificar_duplicatas(self, conn, nome_tabela, df, coluna_pk):
        if not coluna_pk:
            return df, 0
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{nome_tabela}'")
            if not cursor.fetchone():
                return df, 0
            pks_existentes = pd.read_sql(f'SELECT {coluna_pk} FROM "{nome_tabela}"', conn)
            pks_existentes_set = set(pks_existentes[coluna_pk].tolist())
            df_original_len = len(df)
            df_novo = df[~df[coluna_pk].isin(pks_existentes_set)]
            duplicatas = df_original_len - len(df_novo)
            return df_novo, duplicatas
        except Exception as e:
            self.status.emit(f"⚠ Aviso ao verificar duplicatas: {str(e)}")
            return df, 0
    
    def criar_schema_sql(self, df, nome_tabela, tipos):
        colunas_sql = []
        for col in df.columns:
            tipo_usuario = tipos.get(col, 'TEXT')
            colunas_sql.append(f'"{col}" {tipo_usuario}')
        schema = f'CREATE TABLE IF NOT EXISTS "{nome_tabela}" ({", ".join(colunas_sql)})'
        return schema
    
    def converter_tipos_python_para_sqlite(self, df):
        df_convertido = df.copy()
        for col in df_convertido.columns:
            if pd.api.types.is_datetime64_any_dtype(df_convertido[col]):
                df_convertido[col] = df_convertido[col].astype(str)
            elif pd.api.types.is_timedelta64_dtype(df_convertido[col]):
                df_convertido[col] = df_convertido[col].astype(str)
            elif df_convertido[col].dtype == 'object':
                df_convertido[col] = df_convertido[col].apply(
                    lambda x: str(x) if pd.notna(x) and not isinstance(x, (str, int, float)) else x
                )
        return df_convertido
    
    def converter_coluna_tipo(self, df, col_name, tipo_escolhido):
        if tipo_escolhido == 'INTEGER':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce').fillna(0).astype(int)
        elif tipo_escolhido == 'REAL':
            df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
        elif tipo_escolhido == 'BOOLEAN':
            df[col_name] = df[col_name].map({'true': 1, 'false': 0, '1': 1, '0': 0, 'sim': 1, 'não': 0, 'yes': 1, 'no': 0})
        return df

    def run(self):
        try:
            self.status.emit("Iniciando leitura ultra-rápida...")
            
            ext = Path(self.excel_path).suffix.lower()
            if ext == '.csv':
                abas_dict = {'Sheet1': pd.read_csv(self.excel_path, dtype=str, keep_default_na=False)}
                abas = list(abas_dict.keys())
            elif ext in ['.xlsx', '.xls', '.xlsm']:
                xls = pd.ExcelFile(self.excel_path, engine='calamine' if ext == '.xlsx' else 'xlrd')
                abas = xls.sheet_names
                abas_dict = {aba: pd.read_excel(xls, sheet_name=aba, dtype=str, keep_default_na=False) for aba in abas}
            else:
                raise ValueError(f"Formato não suportado: {ext}")
            
            if self.modo == 'append' and self.db_existente_path:
                db_final = self.db_existente_path
                self.status.emit(f"Conectando ao banco existente: {db_final}")
            else:
                db_final = self.db_path
            
            conn = sqlite3.connect(db_final)
            conn.execute("PRAGMA synchronous = OFF")
            conn.execute("PRAGMA journal_mode = MEMORY")
            cursor = conn.cursor()
            
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
                
                colunas_originais = df.columns.tolist()
                
                def normalizar_nome_coluna(nome):
                    normalizado = unicodedata.normalize('NFKD', nome)
                    normalizado = normalizado.encode('ASCII', 'ignore').decode('ASCII')
                    normalizado = re.sub(r'\s+', '_', normalizado)
                    normalizado = re.sub(r'[^a-zA-Z0-9_]', '', normalizado)
                    return normalizado if normalizado else f"coluna_{i}"
                
                df.columns = [normalizar_nome_coluna(col) for col in df.columns]
                
                if self.modo == 'append' and self.db_existente_path:
                    estrutura_existente, tem_pk_existente, _ = self.obter_estrutura_tabela_existente(conn, aba)
                    
                    if estrutura_existente:
                        self.status.emit(f"✓ Usando estrutura existente da tabela '{aba}'")
                        
                        if tem_pk_existente:
                            colunas_pk_existentes = self.obter_metadata_pk(conn, aba)
                            if colunas_pk_existentes:
                                self.status.emit(f"🔑 PK reconstruída: {' + '.join(colunas_pk_existentes)}")
                                df, coluna_pk = self.criar_coluna_pk(df, colunas_pk_existentes)
                                if coluna_pk:
                                    df_novo, duplicatas = self.verificar_duplicatas(conn, aba, df, coluna_pk)
                                    if duplicatas > 0:
                                        self.status.emit(f"⚠ {duplicatas} registros duplicados ignorados em '{aba}'")
                                    df = df_novo
                        
                        colunas_df = [col for col in df.columns if col in estrutura_existente or col == '_PK']
                        df = df[colunas_df]
                        
                        for col_existente in estrutura_existente.keys():
                            if col_existente not in df.columns and col_existente != '_PK':
                                df[col_existente] = None
                        
                        ordem_colunas = list(estrutura_existente.keys())
                        df = df[ordem_colunas]
                        tipos_aba = estrutura_existente
                    else:
                        self.finalizado.emit(False, f"Tabela '{aba}' não existe no banco selecionado.")
                        return
                else:
                    tipos_aba = self.tipo_mapeamento.get(aba, {})
                    colunas_pk_aba = self.colunas_pk.get(aba, [])
                    
                    if colunas_pk_aba:
                        df, coluna_pk = self.criar_coluna_pk(df, colunas_pk_aba)
                        self.salvar_metadata_pk(conn, aba, colunas_pk_aba)
                    else:
                        coluna_pk = None
                    
                    for col_name, tipo_escolhido in tipos_aba.items():
                        if col_name in df.columns and tipo_escolhido != 'TEXT':
                            df = self.converter_coluna_tipo(df, col_name, tipo_escolhido)
                
                df = self.converter_tipos_python_para_sqlite(df)
                
                if self.modo == 'replace':
                    schema_sql = self.criar_schema_sql(df, aba, tipos_aba)
                    conn.execute(f'DROP TABLE IF EXISTS "{aba}"')
                    conn.execute(schema_sql)
                    self.status.emit(f"✓ Tabela '{aba}' criada")
                
                total_linhas = len(df)
                chunksize = 15000
                chunks = [df.iloc[i:i+chunksize] for i in range(0, total_linhas, chunksize)]
                
                for idx_chunk, chunk in enumerate(chunks):
                    chunk.to_sql(aba, conn, if_exists='append', index=False)
                    progresso_parcial = int(((i + (idx_chunk + 1) / len(chunks)) / len(abas)) * 100)
                    self.progresso.emit(progresso_parcial)
                
                self.status.emit(f"✓ {total_linhas} registros inseridos em '{aba}'")
            
            conn.commit()
            conn.close()
            
            self.finalizado.emit(True, f"Conversão concluída!\nBanco: {db_final}")
            
        except Exception as e:
            self.finalizado.emit(False, f"Erro: {str(e)}")


class XMLWorker(QThread):
    """NOVO: Thread para processar XMLs"""
    
    progresso = Signal(int)
    status = Signal(str)
    finalizado = Signal(bool, str, object, object)
    
    def __init__(self, xml_folder):
        super().__init__()
        self.xml_folder = xml_folder
    
    def run(self):
        try:
            if not XML_SUPPORT:
                self.finalizado.emit(False, "xml_processor.py não encontrado", None, None)
                return
            
            self.status.emit("🔍 Escaneando pasta de XMLs...")
            
            processor = XMLProcessor()
            xml_files = list(self.xml_folder.glob('*.xml'))
            total_files = len(xml_files)
            
            if total_files == 0:
                self.finalizado.emit(False, "Nenhum XML encontrado", None, None)
                return
            
            self.status.emit(f"📄 {total_files} arquivo(s) XML encontrado(s)")
            self.progresso.emit(10)
            
            df_nfe, df_cte = processor.process_xml_folder(self.xml_folder)
            
            self.progresso.emit(90)
            
            msg_nfe = f"{len(df_nfe)} NFe" if not df_nfe.empty else "0 NFe"
            msg_cte = f"{len(df_cte)} CTe" if not df_cte.empty else "0 CTe"
            
            self.status.emit(f"✓ Processados: {msg_nfe}, {msg_cte}")
            self.progresso.emit(100)
            
            self.finalizado.emit(True, f"{msg_nfe}, {msg_cte}", df_nfe, df_cte)
            
        except Exception as e:
            self.finalizado.emit(False, f"Erro: {str(e)}", None, None)


# ============================================================================
#  INTERFACE PRINCIPAL
# ============================================================================

class ResponsiveConverter(QWidget):
    """Interface principal - EXPANDIDA com suporte XML"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DataForge Pro v2.0")
        self.setMinimumSize(900, 800)
        
        # Variáveis originais
        self.excel_path = None
        self.db_path_existente = None
        self.preview_data = None
        self.tipo_combos = {}
        self.pk_checkboxes = {}
        
        # NOVO: Variáveis XML
        self.modo_fonte = 'planilha'
        self.xml_folder = None
        self.xml_worker = None
        self.df_nfe = pd.DataFrame()
        self.df_cte = pd.DataFrame()
        
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        
        # Header
        lbl_titulo = QLabel("DataForge Pro v2.0")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setStyleSheet("font-size: 28px; font-weight: bold; color: #BB86FC;")
        
        lbl_subtitulo = QLabel("Excel/CSV/NFe/CTe → SQLite Universal Converter")
        lbl_subtitulo.setAlignment(Qt.AlignCenter)
        lbl_subtitulo.setStyleSheet("font-size: 12px; color: #9E9E9E;")
        
        main_layout.addWidget(lbl_titulo)
        main_layout.addWidget(lbl_subtitulo)
        
        # NOVO: Seletor de tipo de fonte
        if XML_SUPPORT:
            tipo_group = QGroupBox("Tipo de Fonte de Dados")
            tipo_layout = QHBoxLayout(tipo_group)
            
            self.radio_planilha = QRadioButton("📊 Planilhas (Excel/CSV)")
            self.radio_xml = QRadioButton("🧾 XMLs Fiscais (NFe/CTe)")
            self.radio_planilha.setChecked(True)
            
            self.radio_planilha.toggled.connect(lambda: self.alternar_modo('planilha'))
            self.radio_xml.toggled.connect(lambda: self.alternar_modo('xml'))
            
            tipo_layout.addWidget(self.radio_planilha)
            tipo_layout.addWidget(self.radio_xml)
            main_layout.addWidget(tipo_group)
        
        # Container dinâmico
        self.container = QFrame()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Interface Planilha (original)
        self.interface_planilha = QWidget()
        self.setup_interface_planilha()
        self.container_layout.addWidget(self.interface_planilha)
        
        # Interface XML (nova)
        if XML_SUPPORT:
            self.interface_xml = QWidget()
            self.setup_interface_xml()
            self.interface_xml.setVisible(False)
            self.container_layout.addWidget(self.interface_xml)
        
        main_layout.addWidget(self.container)
        
        # Console (compartilhado)
        self.console_group = QGroupBox("Console de Logs")
        console_layout = QVBoxLayout(self.console_group)
        
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(120)
        self.console.setObjectName("console")
        console_layout.addWidget(self.console)
        
        main_layout.addWidget(self.console_group)
        
        # Progress bar (compartilhada)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Botão executar (compartilhado)
        self.btn_run = QPushButton("EXECUTAR CONVERSÃO")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setMinimumHeight(50)
        self.btn_run.clicked.connect(self.executar)
        main_layout.addWidget(self.btn_run)
        
        self.aplicar_estilo()
        self.log("> Aguardando seleção de arquivo...")
    
    def setup_interface_planilha(self):
        """Interface original de planilhas - 100% MANTIDA"""
        layout = QVBoxLayout(self.interface_planilha)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Card de seleção
        self.card_file = QFrame()
        self.card_file.setObjectName("card")
        card_layout = QVBoxLayout(self.card_file)
        
        btn_layout = QHBoxLayout()
        
        self.btn_excel = QPushButton("📁 Selecionar Arquivo")
        self.btn_excel.clicked.connect(self.selecionar_excel)
        
        self.btn_guia = QPushButton("📖 Baixar Guia de Tipos")
        self.btn_guia.clicked.connect(self.baixar_guia_tipos)
        
        btn_layout.addWidget(self.btn_excel)
        btn_layout.addWidget(self.btn_guia)
        
        self.lbl_info = QLabel("Nenhum arquivo selecionado")
        self.lbl_info.setWordWrap(True)
        self.lbl_info.setAlignment(Qt.AlignCenter)
        
        card_layout.addLayout(btn_layout)
        card_layout.addWidget(self.lbl_info)
        layout.addWidget(self.card_file)
        
        # Preview
        self.preview_group = QGroupBox("Preview dos Dados e Tipos")
        self.preview_group.setVisible(False)
        preview_layout = QVBoxLayout(self.preview_group)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)
        
        self.preview_table = QTableWidget()
        self.preview_table.setObjectName("preview_table")
        scroll.setWidget(self.preview_table)
        
        preview_layout.addWidget(scroll)
        layout.addWidget(self.preview_group)
        
        # Opções
        self.opts_group = QGroupBox("Modo de Gravação")
        opts_layout = QVBoxLayout(self.opts_group)
        
        radio_layout = QHBoxLayout()
        self.radio_novo = QRadioButton("Novo Banco (.db)")
        self.radio_append = QRadioButton("Anexar a Banco Existente")
        self.radio_novo.setChecked(True)
        
        radio_layout.addWidget(self.radio_novo)
        radio_layout.addWidget(self.radio_append)
        opts_layout.addLayout(radio_layout)
        
        # Frame banco existente
        self.frame_db_existente = QFrame()
        self.frame_db_existente.setObjectName("card")
        self.frame_db_existente.setVisible(False)
        
        db_existente_layout = QHBoxLayout(self.frame_db_existente)
        self.btn_selecionar_db = QPushButton("📂 Selecionar Banco Existente")
        self.btn_selecionar_db.clicked.connect(self.selecionar_banco_existente)
        
        self.lbl_db_selecionado = QLabel("Nenhum banco selecionado")
        self.lbl_db_selecionado.setWordWrap(True)
        
        db_existente_layout.addWidget(self.btn_selecionar_db)
        db_existente_layout.addWidget(self.lbl_db_selecionado, 1)
        
        opts_layout.addWidget(self.frame_db_existente)
        
        self.radio_novo.toggled.connect(self.atualizar_modo_gravacao)
        self.radio_append.toggled.connect(self.atualizar_modo_gravacao)
        
        layout.addWidget(self.opts_group)
    
    def setup_interface_xml(self):
        """NOVA: Interface para XMLs"""
        layout = QVBoxLayout(self.interface_xml)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Card de seleção de pasta
        card_xml = QFrame()
        card_xml.setObjectName("card")
        card_layout = QVBoxLayout(card_xml)
        
        self.btn_select_xml = QPushButton("📁 Selecionar Pasta com XMLs")
        self.btn_select_xml.setMinimumHeight(50)
        self.btn_select_xml.setStyleSheet("background-color: #BB86FC; color: #000; font-weight: bold;")
        self.btn_select_xml.clicked.connect(self.selecionar_pasta_xml)
        
        self.lbl_xml_info = QLabel("Nenhuma pasta selecionada")
        self.lbl_xml_info.setAlignment(Qt.AlignCenter)
        self.lbl_xml_info.setStyleSheet("color: #9E9E9E;")
        
        card_layout.addWidget(self.btn_select_xml)
        card_layout.addWidget(self.lbl_xml_info)
        layout.addWidget(card_xml)
        
        # Tabs de preview
        self.xml_tabs = QTabWidget()
        
        # Aba NFe
        self.nfe_table = QTableWidget()
        self.nfe_table.setObjectName("preview_table")
        self.xml_tabs.addTab(self.nfe_table, "📄 NFe")
        
        # Aba CTe
        self.cte_table = QTableWidget()
        self.cte_table.setObjectName("preview_table")
        self.xml_tabs.addTab(self.cte_table, "🚚 CTe")
        
        layout.addWidget(self.xml_tabs)
        
        # Botões de ação
        btn_layout = QHBoxLayout()
        
        self.btn_export_xlsx = QPushButton("💾 Exportar para Excel")
        self.btn_export_xlsx.setEnabled(False)
        self.btn_export_xlsx.clicked.connect(self.exportar_xlsx)
        
        self.btn_convert_sqlite = QPushButton("🔄 Converter para SQLite")
        self.btn_convert_sqlite.setEnabled(False)
        self.btn_convert_sqlite.clicked.connect(self.converter_xml_sqlite)
        
        btn_layout.addWidget(self.btn_export_xlsx)
        btn_layout.addWidget(self.btn_convert_sqlite)
        
        layout.addLayout(btn_layout)
    
    # ========================================================================
    #  MÉTODOS ORIGINAIS - 100% MANTIDOS
    # ========================================================================
    
    def selecionar_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Arquivo", "",
            "Arquivos Suportados (*.xlsx *.xls *.csv *.xlsm);;Todos (*.*)"
        )
        if filepath:
            self.excel_path = Path(filepath)
            self.lbl_info.setText(f"Arquivo: {self.excel_path.name}")
            self.log(f"Arquivo selecionado: {filepath}")
            self.carregar_preview()
    
    def carregar_preview(self):
        try:
            ext = self.excel_path.suffix.lower()
            if ext == '.csv':
                df_sample = pd.read_csv(self.excel_path, nrows=100, dtype=str, keep_default_na=False)
                self.preview_data = {'Sheet1': df_sample}
            elif ext in ['.xlsx', '.xls', '.xlsm']:
                xls = pd.ExcelFile(self.excel_path, engine='calamine' if ext == '.xlsx' else 'xlrd')
                primeira_aba = xls.sheet_names[0]
                df_sample = pd.read_excel(xls, sheet_name=primeira_aba, nrows=100, dtype=str, keep_default_na=False)
                self.preview_data = {primeira_aba: df_sample}
            else:
                raise ValueError("Formato não suportado")
            
            primeira_aba = list(self.preview_data.keys())[0]
            self.mostrar_preview(primeira_aba)
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar preview: {str(e)}")
    
    def mostrar_preview(self, sheet_name):
        df = self.preview_data[sheet_name]
        
        def normalizar_nome_coluna(nome):
            normalizado = unicodedata.normalize('NFKD', nome)
            normalizado = normalizado.encode('ASCII', 'ignore').decode('ASCII')
            normalizado = re.sub(r'\s+', '_', normalizado)
            normalizado = re.sub(r'[^a-zA-Z0-9_]', '', normalizado)
            return normalizado if normalizado else "coluna"
        
        colunas_normalizadas = [normalizar_nome_coluna(c) for c in df.columns]
        
        num_colunas = len(colunas_normalizadas)
        self.preview_table.setRowCount(7)
        self.preview_table.setColumnCount(num_colunas)
        self.preview_table.setHorizontalHeaderLabels(colunas_normalizadas)
        
        def detectar_tipo_coluna(serie):
            amostra = serie.dropna().astype(str).head(100)
            if len(amostra) == 0:
                return 'TEXT'
            
            try:
                pd.to_numeric(amostra, errors='raise')
                if all(amostra.str.contains(r'^\d+$', na=False)):
                    return 'INTEGER'
                else:
                    return 'REAL'
            except:
                pass
            
            try:
                pd.to_datetime(amostra, errors='raise')
                if any(amostra.str.contains(r'\d{2}:\d{2}', na=False)):
                    return 'DATETIME'
                else:
                    return 'DATE'
            except:
                pass
            
            unicos = amostra.unique()
            if len(unicos) == 2 and set(map(str.lower, unicos)) <= {'true', 'false', '1', '0', 'sim', 'não', 'yes', 'no'}:
                return 'BOOLEAN'
            
            return 'TEXT'
        
        self.tipo_combos[sheet_name] = {}
        self.pk_checkboxes[sheet_name] = {}
        
        for col_idx, (col_original, col_normalizada) in enumerate(zip(df.columns, colunas_normalizadas)):
            tipo_detectado = detectar_tipo_coluna(df[col_original])
            
            combo = QComboBox()
            combo.addItems(['TEXT', 'INTEGER', 'REAL', 'NUMERIC', 'BLOB', 'DATE', 'DATETIME', 'TIME', 'BOOLEAN'])
            combo.setCurrentText(tipo_detectado)
            combo.setObjectName("combo_tipo")
            self.preview_table.setCellWidget(0, col_idx, combo)
            self.tipo_combos[sheet_name][col_normalizada] = combo
            
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin-left: 50%; }")
            self.preview_table.setCellWidget(1, col_idx, checkbox)
            self.pk_checkboxes[sheet_name][col_normalizada] = checkbox
            
            info_item = QTableWidgetItem("─────")
            info_item.setTextAlignment(Qt.AlignCenter)
            info_item.setFlags(info_item.flags() & ~Qt.ItemIsEditable)
            self.preview_table.setItem(2, col_idx, info_item)
            
            for row_offset in range(4):
                if row_offset < len(df):
                    valor = str(df.iloc[row_offset, col_idx])
                    item = QTableWidgetItem(valor)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.preview_table.setItem(3 + row_offset, col_idx, item)
        
        header_vertical = ['Tipo SQL', 'Chave PK?', '────────']
        header_vertical.extend([f'Linha {i+1}' for i in range(4)])
        self.preview_table.setVerticalHeaderLabels(header_vertical)
        
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.preview_group.setVisible(True)
        self.log(f"Preview carregado: {len(df.columns)} colunas, {len(df)} linhas")
    
    def atualizar_modo_gravacao(self):
        if self.radio_append.isChecked():
            self.frame_db_existente.setVisible(True)
        else:
            self.frame_db_existente.setVisible(False)
            self.db_path_existente = None
            self.lbl_db_selecionado.setText("Nenhum banco selecionado")
    
    def selecionar_banco_existente(self):
        db_path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar Banco de Dados Existente", "",
            "SQLite Database (*.db);;Todos (*.*)"
        )
        if db_path:
            self.db_path_existente = Path(db_path)
            self.lbl_db_selecionado.setText(f"Banco: {self.db_path_existente.name}")
            self.log(f"Banco existente selecionado: {db_path}")
            self.analisar_banco_existente()
    
    def analisar_banco_existente(self):
        try:
            conn = sqlite3.connect(self.db_path_existente)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE '_%'")
            tabelas = [row[0] for row in cursor.fetchall()]
            
            if not tabelas:
                self.log("⚠ Banco não contém tabelas")
                conn.close()
                return
            
            self.log(f"📊 Banco contém {len(tabelas)} tabela(s): {', '.join(tabelas)}")
            
            for tabela in tabelas:
                cursor.execute(f'PRAGMA table_info("{tabela}")')
                colunas_info = cursor.fetchall()
                colunas = [f"{col[1]} ({col[2]})" for col in colunas_info]
                
                cursor.execute("SELECT colunas_pk FROM _dataforge_metadata WHERE tabela = ?", (tabela,))
                resultado = cursor.fetchone()
                
                if resultado and resultado[0]:
                    pk_info = f"  🔑 PK formada por: {resultado[0].replace(',', ' + ')}"
                else:
                    pk_info = "  ℹ Sem PK definida"
                
                self.log(f"  • {tabela}: {', '.join(colunas)}")
                self.log(pk_info)
            
            conn.close()
            
        except Exception as e:
            self.log(f"❌ Erro ao analisar banco: {str(e)}")
    
    def baixar_guia_tipos(self):
        guia_conteudo = """
===========================================
GUIA DE TIPOS SQLITE - DataForge Pro
===========================================

1. TEXT
   - Texto de qualquer tamanho
   - Uso: nomes, descrições, endereços, IDs alfanuméricos
   - Exemplos: "João Silva", "Rua ABC", "12345-ABC"

2. INTEGER
   - Números inteiros (sem casas decimais)
   - Uso: contagens, IDs numéricos, anos, quantidades
   - Exemplos: 42, -10, 2024, 1000

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
DataForge Pro v2.0
===========================================
"""
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Guia de Tipos", "Guia_Tipos_SQLite.txt", "Arquivo de Texto (*.txt)"
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
        """Executa conversão baseada no modo"""
        if self.modo_fonte == 'planilha':
            self.executar_planilha()
        elif self.modo_fonte == 'xml':
            self.executar_xml()
    
    def executar_planilha(self):
        """Execução original de planilhas"""
        if not self.excel_path:
            return QMessageBox.warning(self, "Aviso", "Selecione um arquivo primeiro.")
        
        if not self.preview_data:
            return QMessageBox.warning(self, "Aviso", "Preview não carregado.")
        
        modo = "replace" if self.radio_novo.isChecked() else "append"
        
        if modo == "append" and not self.db_path_existente:
            return QMessageBox.warning(self, "Aviso", "Selecione o banco existente.")
        
        if modo == "append":
            db_path = self.db_path_existente
        else:
            db_path = self.excel_path.parent / f"{self.excel_path.stem}.db"
        
        tipo_mapeamento = {}
        for sheet_name, combos in self.tipo_combos.items():
            tipo_mapeamento[sheet_name] = {
                col_name: combo.currentText() 
                for col_name, combo in combos.items()
            }
        
        colunas_pk = {}
        for sheet_name, checkboxes in self.pk_checkboxes.items():
            colunas_selecionadas = [
                col_name for col_name, checkbox in checkboxes.items() 
                if checkbox.isChecked()
            ]
            if colunas_selecionadas:
                colunas_pk[sheet_name] = colunas_selecionadas
                if modo == "replace":
                    self.log(f"🔑 PK: {' + '.join(colunas_selecionadas)}")
            else:
                colunas_pk[sheet_name] = []
        
        if modo == "append":
            self.log("ℹ Modo ANEXAR: Usando estrutura existente")
        
        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        db_existente = self.db_path_existente if modo == "append" else None
        
        self.worker = ConversorWorker(
            self.excel_path, db_path, modo, self.preview_data, 
            tipo_mapeamento, colunas_pk, db_existente
        )
        self.worker.status.connect(self.log)
        self.worker.progresso.connect(self.progress_bar.setValue)
        self.worker.finalizado.connect(self.concluir)
        self.worker.start()
    
    # ========================================================================
    #  MÉTODOS NOVOS - XML
    # ========================================================================
    
    def alternar_modo(self, modo):
        """Alterna entre interface de planilha e XML"""
        if modo == 'planilha':
            self.interface_planilha.setVisible(True)
            if hasattr(self, 'interface_xml'):
                self.interface_xml.setVisible(False)
            self.modo_fonte = 'planilha'
            self.log("📊 Modo: Planilhas (Excel/CSV)")
        elif modo == 'xml':
            self.interface_planilha.setVisible(False)
            if hasattr(self, 'interface_xml'):
                self.interface_xml.setVisible(True)
            self.modo_fonte = 'xml'
            self.log("🧾 Modo: XMLs Fiscais (NFe/CTe)")
    
    def selecionar_pasta_xml(self):
        """Seleciona pasta com XMLs"""
        pasta = QFileDialog.getExistingDirectory(self, "Selecionar Pasta com XMLs", "")
        
        if not pasta:
            return
        
        self.xml_folder = Path(pasta)
        self.lbl_xml_info.setText(f"Pasta: {self.xml_folder.name}")
        self.log(f"📁 Pasta XML: {pasta}")
        
        self.processar_xmls()
    
    def processar_xmls(self):
        """Processa XMLs da pasta"""
        if not self.xml_folder:
            return
        
        self.btn_run.setEnabled(False)
        self.btn_export_xlsx.setEnabled(False)
        self.btn_convert_sqlite.setEnabled(False)
        
        self.xml_worker = XMLWorker(self.xml_folder)
        self.xml_worker.status.connect(self.log)
        self.xml_worker.progresso.connect(self.progress_bar.setValue)
        self.xml_worker.finalizado.connect(self.xml_processado)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.xml_worker.start()
    
    def xml_processado(self, sucesso, msg, df_nfe, df_cte):
        """Callback quando XML termina"""
        self.progress_bar.setVisible(False)
        self.btn_run.setEnabled(True)
        
        if not sucesso:
            QMessageBox.critical(self, "Erro", msg)
            self.log(f"❌ {msg}")
            return
        
        self.df_nfe = df_nfe if df_nfe is not None else pd.DataFrame()
        self.df_cte = df_cte if df_cte is not None else pd.DataFrame()
        
        self.log(f"✓ {msg}")
        
        # Popula preview
        self.popular_tabela_xml(self.nfe_table, self.df_nfe, "NFe")
        self.popular_tabela_xml(self.cte_table, self.df_cte, "CTe")
        
        # Habilita botões
        if not self.df_nfe.empty or not self.df_cte.empty:
            self.btn_export_xlsx.setEnabled(True)
            self.btn_convert_sqlite.setEnabled(True)
    
    def popular_tabela_xml(self, table, df, tipo):
        """Popula tabela de preview com dados XML"""
        if df.empty:
            table.setRowCount(1)
            table.setColumnCount(1)
            table.setItem(0, 0, QTableWidgetItem(f"Nenhum {tipo} encontrado"))
            return
        
        max_rows = min(100, len(df))
        table.setRowCount(max_rows)
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns.tolist())
        
        for row_idx in range(max_rows):
            for col_idx, col_name in enumerate(df.columns):
                value = str(df.iloc[row_idx, col_idx])
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_idx, col_idx, item)
        
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.log(f"✓ Preview {tipo}: {len(df)} registros, {len(df.columns)} colunas")
    
    def exportar_xlsx(self):
        """Exporta XMLs para Excel"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Salvar Excel", "xmls_processados.xlsx", "Excel (*.xlsx)"
        )
        
        if not filepath:
            return
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                if not self.df_nfe.empty:
                    self.df_nfe.to_excel(writer, sheet_name='NFe', index=False)
                if not self.df_cte.empty:
                    self.df_cte.to_excel(writer, sheet_name='CTe', index=False)
            
            QMessageBox.information(self, "Sucesso", f"Excel salvo:\n{filepath}")
            self.log(f"✓ Excel exportado: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro: {str(e)}")
    
    def executar_xml(self):
        """Placeholder - botão principal redireciona para converter_xml_sqlite"""
        self.converter_xml_sqlite()
    
    def converter_xml_sqlite(self):
        """Converte XMLs para SQLite"""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Salvar SQLite", "xmls_fiscal.db", "SQLite (*.db)"
        )
        
        if not filepath:
            return
        
        try:
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            
            # Cria tabela de metadados
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS _dataforge_metadata (
                    tabela TEXT PRIMARY KEY,
                    colunas_pk TEXT,
                    data_criacao TEXT
                )
            """)
            
            # Salva NFe
            if not self.df_nfe.empty:
                df_nfe_copy = self.df_nfe.copy()
                if 'Chave NFe' in df_nfe_copy.columns:
                    df_nfe_copy['_PK'] = df_nfe_copy['Chave NFe']
                
                df_nfe_copy.to_sql('NFe', conn, if_exists='replace', index=False)
                self.log(f"✓ Tabela NFe: {len(df_nfe_copy)} registros")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO _dataforge_metadata 
                    VALUES ('NFe', 'Chave NFe', datetime('now'))
                """)
            
            # Salva CTe
            if not self.df_cte.empty:
                df_cte_copy = self.df_cte.copy()
                if 'Chave CTE' in df_cte_copy.columns:
                    df_cte_copy['_PK'] = df_cte_copy['Chave CTE']
                
                df_cte_copy.to_sql('CTe', conn, if_exists='replace', index=False)
                self.log(f"✓ Tabela CTe: {len(df_cte_copy)} registros")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO _dataforge_metadata 
                    VALUES ('CTe', 'Chave CTE', datetime('now'))
                """)
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Sucesso", f"SQLite criado:\n{filepath}")
            self.log(f"✓ Banco criado: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro: {str(e)}")
    
    def concluir(self, sucesso, msg):
        """Callback de conclusão"""
        self.btn_run.setEnabled(True)
        if sucesso:
            self.log("✓ Operação finalizada")
            QMessageBox.information(self, "Sucesso", msg)
            self.resetar_interface()
        else:
            self.log(f"❌ ERRO: {msg}")
            QMessageBox.critical(self, "Erro", msg)
    
    def resetar_interface(self):
        """Reset completo da interface"""
        # Planilha
        self.excel_path = None
        self.db_path_existente = None
        self.preview_data = None
        self.tipo_combos = {}
        self.pk_checkboxes = {}
        
        self.lbl_info.setText("Nenhum arquivo selecionado")
        self.lbl_db_selecionado.setText("Nenhum banco selecionado")
        
        self.preview_group.setVisible(False)
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        
        self.frame_db_existente.setVisible(False)
        self.radio_novo.setChecked(True)
        
        # XML
        self.xml_folder = None
        self.df_nfe = pd.DataFrame()
        self.df_cte = pd.DataFrame()
        
        if hasattr(self, 'lbl_xml_info'):
            self.lbl_xml_info.setText("Nenhuma pasta selecionada")
            self.btn_export_xlsx.setEnabled(False)
            self.btn_convert_sqlite.setEnabled(False)
            
            self.nfe_table.setRowCount(0)
            self.nfe_table.setColumnCount(0)
            self.cte_table.setRowCount(0)
            self.cte_table.setColumnCount(0)
        
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
        self.log("🔄 Interface resetada")
    
    def log(self, msg):
        """Log no console"""
        self.console.appendPlainText(msg)
        self.console.verticalScrollBar().setValue(
            self.console.verticalScrollBar().maximum()
        )
    
    def aplicar_estilo(self):
        """Aplica dark theme"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
            }
            
            QGroupBox {
                border: 1px solid #333;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            
            #card {
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 10px;
                padding: 15px;
            }
            
            QPushButton {
                background-color: #333;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                border: 1px solid #444;
                min-height: 35px;
            }
            
            QPushButton:hover {
                background-color: #444;
                border: 1px solid #BB86FC;
            }
            
            #btn_run {
                background-color: #BB86FC;
                color: #000;
                font-size: 14px;
                font-weight: bold;
            }
            
            #btn_run:hover {
                background-color: #D7B7FD;
            }
            
            #console {
                background-color: #0D0D0D;
                border: 1px solid #333;
                border-radius: 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                padding: 8px;
            }
            
            #preview_table {
                background-color: #252525;
                alternate-background-color: #2A2A2A;
                gridline-color: #333;
                border: 1px solid #444;
            }
            
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #E0E0E0;
                padding: 5px;
                border: 1px solid #444;
                font-weight: bold;
            }
            
            #combo_tipo {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 3px;
            }
            
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            
            QProgressBar {
                border: 1px solid #333;
                border-radius: 8px;
                background-color: #252525;
                text-align: center;
                height: 25px;
            }
            
            QProgressBar::chunk {
                background-color: #BB86FC;
                border-radius: 7px;
            }
            
            QTabWidget::pane {
                border: 1px solid #333;
                border-radius: 8px;
                background-color: #1E1E1E;
            }
            
            QTabBar::tab {
                background-color: #252525;
                color: #9E9E9E;
                border: 1px solid #333;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 15px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #BB86FC;
                color: #000;
                font-weight: bold;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    if not XML_SUPPORT:
        QMessageBox.warning(
            None, "Aviso",
            "xml_processor.py não encontrado.\n\n"
            "Funcionalidades XML desabilitadas.\n"
            "Apenas Excel/CSV disponíveis."
        )
    
    win = ResponsiveConverter()
    win.show()
    sys.exit(app.exec())
