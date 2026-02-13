"""
DataForge Pro - Extensão XML
Módulo que adiciona suporte a NFe/CTe ao DataForge Pro existente
Importar este módulo no arquivo principal para ativar funcionalidades XML
"""

import pandas as pd
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import QThread, Signal, Qt
from xml_processor import XMLProcessor


class XMLWorker(QThread):
    """Thread para processamento assíncrono de XMLs"""
    
    progresso = Signal(int)
    status = Signal(str)
    finalizado = Signal(bool, str, object, object)  # (sucesso, msg, df_nfe, df_cte)
    
    def __init__(self, xml_folder):
        super().__init__()
        self.xml_folder = xml_folder
    
    def run(self):
        try:
            self.status.emit("🔍 Escaneando pasta de XMLs...")
            
            processor = XMLProcessor()
            xml_files = list(self.xml_folder.glob('*.xml'))
            total_files = len(xml_files)
            
            if total_files == 0:
                self.finalizado.emit(False, "Nenhum arquivo XML encontrado na pasta", None, None)
                return
            
            self.status.emit(f"📄 {total_files} arquivo(s) XML encontrado(s)")
            self.progresso.emit(10)
            
            # Processa todos os XMLs
            df_nfe, df_cte = processor.process_xml_folder(self.xml_folder)
            
            self.progresso.emit(90)
            
            # Resultado
            msg_nfe = f"{len(df_nfe)} NFe" if not df_nfe.empty else "0 NFe"
            msg_cte = f"{len(df_cte)} CTe" if not df_cte.empty else "0 CTe"
            
            self.status.emit(f"✓ Processamento concluído: {msg_nfe}, {msg_cte}")
            self.progresso.emit(100)
            
            self.finalizado.emit(True, f"Processados: {msg_nfe}, {msg_cte}", df_nfe, df_cte)
            
        except Exception as e:
            self.finalizado.emit(False, f"Erro ao processar XMLs: {str(e)}", None, None)


class XMLPreviewWidget(QWidget):
    """Widget de preview para dados XML processados"""
    
    def __init__(self, parent_log_function):
        super().__init__()
        self.log = parent_log_function
        self.df_nfe = pd.DataFrame()
        self.df_cte = pd.DataFrame()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label informativo
        self.info_label = QLabel("Nenhum XML processado")
        self.info_label.setStyleSheet("color: #9E9E9E; font-size: 12px;")
        layout.addWidget(self.info_label)
        
        # Tabs para NFe e CTe
        self.tabs = QTabWidget()
        self.tabs.setObjectName("xml_tabs")
        
        # Aba NFe
        self.nfe_table = QTableWidget()
        self.nfe_table.setObjectName("preview_table")
        self.tabs.addTab(self.nfe_table, "📄 NFe")
        
        # Aba CTe
        self.cte_table = QTableWidget()
        self.cte_table.setObjectName("preview_table")
        self.tabs.addTab(self.cte_table, "🚚 CTe")
        
        layout.addWidget(self.tabs)
        
        # Botões de ação
        btn_layout = QHBoxLayout()
        
        self.btn_export_xlsx = QPushButton("💾 Exportar para Excel")
        self.btn_export_xlsx.setObjectName("btn_action")
        self.btn_export_xlsx.clicked.connect(self.export_to_xlsx)
        self.btn_export_xlsx.setEnabled(False)
        
        self.btn_convert_db = QPushButton("🔄 Converter para SQLite")
        self.btn_convert_db.setObjectName("btn_action")
        self.btn_convert_db.clicked.connect(self.convert_to_sqlite)
        self.btn_convert_db.setEnabled(False)
        
        btn_layout.addWidget(self.btn_export_xlsx)
        btn_layout.addWidget(self.btn_convert_db)
        
        layout.addLayout(btn_layout)
        
        # Estilo dos botões
        self.setStyleSheet("""
            #btn_action {
                background-color: #333;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                border: 1px solid #444;
                min-height: 40px;
            }
            #btn_action:hover {
                background-color: #444;
                border: 1px solid #BB86FC;
            }
            #btn_action:disabled {
                background-color: #222;
                color: #555;
            }
            #xml_tabs {
                background-color: #1E1E1E;
            }
            #xml_tabs::pane {
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
    
    def load_data(self, df_nfe: pd.DataFrame, df_cte: pd.DataFrame):
        """Carrega dados processados e atualiza preview"""
        self.df_nfe = df_nfe if df_nfe is not None else pd.DataFrame()
        self.df_cte = df_cte if df_cte is not None else pd.DataFrame()
        
        # Atualiza label
        msg_parts = []
        if not self.df_nfe.empty:
            msg_parts.append(f"{len(self.df_nfe)} NFe")
        if not self.df_cte.empty:
            msg_parts.append(f"{len(self.df_cte)} CTe")
        
        if msg_parts:
            self.info_label.setText(f"✓ Dados carregados: {', '.join(msg_parts)}")
            self.btn_export_xlsx.setEnabled(True)
            self.btn_convert_db.setEnabled(True)
        else:
            self.info_label.setText("⚠ Nenhum dado encontrado")
            self.btn_export_xlsx.setEnabled(False)
            self.btn_convert_db.setEnabled(False)
        
        # Popula tabelas de preview (primeiras 100 linhas)
        self._populate_table(self.nfe_table, self.df_nfe.head(100))
        self._populate_table(self.cte_table, self.df_cte.head(100))
        
        self.log(f"✓ Preview atualizado: {', '.join(msg_parts) if msg_parts else 'Sem dados'}")
    
    def _populate_table(self, table: QTableWidget, df: pd.DataFrame):
        """Popula QTableWidget com dados do DataFrame"""
        if df.empty:
            table.setRowCount(0)
            table.setColumnCount(0)
            return
        
        # Configura tabela
        table.setRowCount(min(len(df), 100))
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns.tolist())
        
        # Popula dados
        for row_idx in range(min(len(df), 100)):
            for col_idx, col_name in enumerate(df.columns):
                value = str(df.iloc[row_idx, col_idx])
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_idx, col_idx, item)
        
        # Ajusta colunas
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    
    def export_to_xlsx(self):
        """Exporta dados para Excel"""
        if self.df_nfe.empty and self.df_cte.empty:
            QMessageBox.warning(self, "Aviso", "Nenhum dado para exportar")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Excel",
            "xmls_processados.xlsx",
            "Excel (*.xlsx)"
        )
        
        if not filepath:
            return
        
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                if not self.df_nfe.empty:
                    self.df_nfe.to_excel(writer, sheet_name='NFe', index=False)
                if not self.df_cte.empty:
                    self.df_cte.to_excel(writer, sheet_name='CTe', index=False)
            
            QMessageBox.information(self, "Sucesso", f"Arquivo salvo:\n{filepath}")
            self.log(f"✓ Excel exportado: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar Excel:\n{str(e)}")
            self.log(f"❌ Erro ao exportar Excel: {str(e)}")
    
    def convert_to_sqlite(self):
        """Converte dados para SQLite"""
        if self.df_nfe.empty and self.df_cte.empty:
            QMessageBox.warning(self, "Aviso", "Nenhum dado para converter")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Banco SQLite",
            "xmls_fiscal.db",
            "SQLite Database (*.db)"
        )
        
        if not filepath:
            return
        
        try:
            import sqlite3
            
            conn = sqlite3.connect(filepath)
            
            # Salva NFe
            if not self.df_nfe.empty:
                # Cria chave primária baseada na Chave NFe
                df_nfe_copy = self.df_nfe.copy()
                if 'Chave NFe' in df_nfe_copy.columns:
                    df_nfe_copy['_PK'] = df_nfe_copy['Chave NFe']
                
                df_nfe_copy.to_sql('NFe', conn, if_exists='replace', index=False)
                self.log(f"✓ Tabela NFe criada: {len(df_nfe_copy)} registros")
                
                # Salva metadados
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS _dataforge_metadata (
                        tabela TEXT PRIMARY KEY,
                        colunas_pk TEXT,
                        data_criacao TEXT
                    )
                """)
                cursor.execute("""
                    INSERT OR REPLACE INTO _dataforge_metadata VALUES ('NFe', 'Chave NFe', datetime('now'))
                """)
            
            # Salva CTe
            if not self.df_cte.empty:
                df_cte_copy = self.df_cte.copy()
                if 'Chave CTE' in df_cte_copy.columns:
                    df_cte_copy['_PK'] = df_cte_copy['Chave CTE']
                
                df_cte_copy.to_sql('CTe', conn, if_exists='replace', index=False)
                self.log(f"✓ Tabela CTe criada: {len(df_cte_copy)} registros")
                
                cursor.execute("""
                    INSERT OR REPLACE INTO _dataforge_metadata VALUES ('CTe', 'Chave CTE', datetime('now'))
                """)
            
            conn.commit()
            conn.close()
            
            QMessageBox.information(self, "Sucesso", f"Banco de dados salvo:\n{filepath}")
            self.log(f"✓ SQLite criado: {filepath}")
            
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao criar banco:\n{str(e)}")
            self.log(f"❌ Erro ao criar SQLite: {str(e)}")
    
    def clear_data(self):
        """Limpa dados e preview"""
        self.df_nfe = pd.DataFrame()
        self.df_cte = pd.DataFrame()
        self.nfe_table.setRowCount(0)
        self.nfe_table.setColumnCount(0)
        self.cte_table.setRowCount(0)
        self.cte_table.setColumnCount(0)
        self.info_label.setText("Nenhum XML processado")
        self.btn_export_xlsx.setEnabled(False)
        self.btn_convert_db.setEnabled(False)


def create_xml_interface(parent_log_function):
    """
    Factory function para criar interface XML
    Retorna QWidget com interface completa
    """
    xml_widget = QWidget()
    xml_layout = QVBoxLayout(xml_widget)
    xml_layout.setContentsMargins(0, 0, 0, 0)
    
    # Card de seleção
    card_xml = QGroupBox("Processamento de XMLs Fiscais")
    card_layout = QVBoxLayout(card_xml)
    
    btn_select_folder = QPushButton("📁 Selecionar Pasta com XMLs")
    btn_select_folder.setObjectName("btn_select_xml")
    btn_select_folder.setMinimumHeight(50)
    
    label_info = QLabel("Nenhuma pasta selecionada")
    label_info.setAlignment(Qt.AlignCenter)
    label_info.setStyleSheet("color: #9E9E9E;")
    
    card_layout.addWidget(btn_select_folder)
    card_layout.addWidget(label_info)
    
    xml_layout.addWidget(card_xml)
    
    # Preview widget
    preview_widget = XMLPreviewWidget(parent_log_function)
    xml_layout.addWidget(preview_widget)
    
    # Estilo do botão
    xml_widget.setStyleSheet("""
        #btn_select_xml {
            background-color: #BB86FC;
            color: #000;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
        }
        #btn_select_xml:hover {
            background-color: #D7B7FD;
        }
    """)
    
    # Armazena referências para acesso externo
    xml_widget.btn_select_folder = btn_select_folder
    xml_widget.label_info = label_info
    xml_widget.preview_widget = preview_widget
    
    return xml_widget
