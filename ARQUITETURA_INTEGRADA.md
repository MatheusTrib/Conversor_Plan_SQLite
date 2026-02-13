# 🏗️ DataForge Pro - Arquitetura Integrada v2.0

## 📋 Estrutura de Arquivos

```
dataforge_pro/
├── dataforge_pro_main.py          # ✅ ARQUIVO PRINCIPAL (UI unificada)
├── xml_processor.py                # Processador XML (módulo separado)
├── requirements.txt                # Dependências completas
├── README.md                       # Documentação completa
└── docs/
    ├── TECHNICAL_GUIDE.md          # Guia técnico
    └── XML_MODULE_DOCS.md          # Docs específicas XML
```

---

## 🎯 Decisões de Arquitetura

### ✅ O Que Manter (100% Preservado)

1. **Interface Atual do Excel/CSV**
   - Preview de tabela
   - Seleção de tipos
   - Checkboxes de PK
   - Modo Replace/Append
   - Normalização de colunas
   - Sistema de metadados
   - Todos os logs e mensagens

2. **Funcionalidades Core**
   - ConversorWorker (thread assíncrona)
   - Detecção automática de tipos
   - Verificação de duplicatas
   - Guia de tipos (botão)
   - Reset automático da interface

3. **Design e UX**
   - Dark theme
   - Paleta de cores atual
   - Responsividade
   - Todos os estilos CSS

---

### ✨ O Que Adicionar (Integrado)

1. **Seletor de Tipo de Arquivo**
   - Radio buttons: `Planilhas (Excel/CSV)` | `XMLs Fiscais (NFe/CTe)`
   - Muda interface dinamicamente

2. **Interface XML** (quando selecionado)
   - Botão: "Selecionar Pasta de XMLs"
   - Preview em ABAS (NFe | CTe)
   - Tabela resumo (X NFe, Y CTe encontrados)
   - Botões: "Exportar XLSX" | "Converter para SQLite"

3. **Worker XML**
   - XMLWorker (similar ao ConversorWorker)
   - Processa pasta em thread separada
   - Signals de progresso

---

## 🔀 Fluxo de Uso

### Modo 1: Excel/CSV (Original - 100% Mantido)

```
Início
  │
  ├─> [Radio: Planilhas]
  │
  ├─> Selecionar arquivo .xlsx/.csv
  │
  ├─> Preview com tipos e PKs
  │
  ├─> Escolher modo (Novo/Append)
  │
  ├─> Executar → SQLite
  │
  └─> Reset → Pronto para próximo
```

### Modo 2: XML (Novo - Integrado)

```
Início
  │
  ├─> [Radio: XMLs Fiscais]
  │
  ├─> Interface muda para modo XML
  │
  ├─> Selecionar pasta com XMLs
  │
  ├─> Processamento automático
  │
  ├─> Preview em abas:
  │     ├─> Aba NFe (X registros)
  │     └─> Aba CTe (Y registros)
  │
  ├─> Opção 1: Exportar XLSX
  │     └─> Excel com 2 abas
  │
  ├─> Opção 2: Converter SQLite
  │     ├─> Tabela: NFe
  │     ├─> Tabela: CTe
  │     └─> Mesmo sistema de PK
  │
  └─> Reset → Pronto para próximo
```

---

## 🎨 Layout da Interface Integrada

```
┌────────────────────────────────────────────────────┐
│  DataForge Pro - Conversor Universal               │
│  XLSX/CSV/NFe/CTe para SQLite Engine              │
├────────────────────────────────────────────────────┤
│                                                     │
│  Tipo de Fonte:                                    │
│  ○ Planilhas (Excel/CSV)  ○ XMLs Fiscais (NFe/CTe)│
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │  [Interface dinâmica baseada na seleção]    │ │
│  │                                              │ │
│  │  SE Planilhas:                               │ │
│  │    → Botão "Selecionar Arquivo"             │ │
│  │    → Preview de colunas                     │ │
│  │    → Tipos e PKs                            │ │
│  │                                              │ │
│  │  SE XMLs:                                    │ │
│  │    → Botão "Selecionar Pasta XMLs"         │ │
│  │    → Tabs: NFe | CTe                       │ │
│  │    → Preview de dados processados          │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ Console de Logs ─────────────────────────┐   │
│  │ > Aguardando seleção...                   │   │
│  └───────────────────────────────────────────┘   │
│                                                     │
│  [████████████░░░░░░░░░░] 60%                     │
│                                                     │
│  [EXECUTAR CONVERSÃO]                              │
└────────────────────────────────────────────────────┘
```

---

## 💻 Implementação Técnica

### Estrutura de Classes

```python
# ARQUIVO: dataforge_pro_main.py

class ResponsiveConverter(QWidget):
    """Interface principal - MODIFICADA para suportar XMLs"""
    
    def __init__(self):
        self.modo_fonte = 'planilha'  # ou 'xml'
        self.excel_path = None
        self.xml_folder = None
        self.df_nfe = None
        self.df_cte = None
        # ... resto mantido igual
    
    def init_ui(self):
        # Header (mantido)
        # Radio buttons TIPO DE FONTE (NOVO)
        # Container dinâmico (muda baseado na seleção)
        # Console (mantido)
        # Botão executar (mantido)
    
    def alternar_modo_fonte(self, modo):
        """NOVO: Alterna entre planilha e XML"""
        if modo == 'planilha':
            self.mostrar_interface_planilha()
        elif modo == 'xml':
            self.mostrar_interface_xml()
    
    def mostrar_interface_planilha(self):
        """Mostra interface original (100% mantida)"""
        # Card de seleção de arquivo
        # Preview de tabela
        # Tipos e PKs
        # Modo replace/append
    
    def mostrar_interface_xml(self):
        """NOVO: Mostra interface XML"""
        # Botão selecionar pasta
        # Tabs NFe/CTe
        # Botões: Exportar XLSX, Converter SQLite
    
    # Métodos originais TODOS mantidos:
    # - selecionar_excel()
    # - carregar_preview()
    # - mostrar_preview()
    # - detectar_tipo_coluna()
    # - normalizar_nome_coluna()
    # - baixar_guia_tipos()
    # - executar()
    # - concluir()
    # - resetar_interface()


class ConversorWorker(QThread):
    """Thread para processar Excel/CSV - 100% MANTIDO"""
    # ... código original sem modificações


class XMLWorker(QThread):
    """NOVO: Thread para processar XMLs"""
    
    progresso = Signal(int)
    status = Signal(str)
    finalizado = Signal(bool, str, object, object)  # (sucesso, msg, df_nfe, df_cte)
    
    def __init__(self, xml_folder):
        super().__init__()
        self.xml_folder = xml_folder
    
    def run(self):
        from xml_processor import XMLProcessor
        
        processor = XMLProcessor()
        df_nfe, df_cte = processor.process_xml_folder(self.xml_folder)
        
        # Emite resultados
        self.finalizado.emit(True, "Processamento concluído", df_nfe, df_cte)
```

---

## 🔧 Modificações Necessárias

### 1. Adicionar Radio Buttons de Tipo

```python
# Em init_ui(), após o header:

tipo_group = QGroupBox("Tipo de Fonte de Dados")
tipo_layout = QHBoxLayout(tipo_group)

self.radio_planilha = QRadioButton("📊 Planilhas (Excel/CSV)")
self.radio_xml = QRadioButton("🧾 XMLs Fiscais (NFe/CTe)")
self.radio_planilha.setChecked(True)

self.radio_planilha.toggled.connect(lambda: self.alternar_modo_fonte('planilha'))
self.radio_xml.toggled.connect(lambda: self.alternar_modo_fonte('xml'))

tipo_layout.addWidget(self.radio_planilha)
tipo_layout.addWidget(self.radio_xml)

main_layout.addWidget(tipo_group)
```

### 2. Container Dinâmico

```python
# Container que muda de conteúdo
self.container_dinamico = QFrame()
self.container_layout = QVBoxLayout(self.container_dinamico)

# Inicialmente mostra interface de planilha
self.interface_planilha = self.criar_interface_planilha()
self.interface_xml = self.criar_interface_xml()

self.container_layout.addWidget(self.interface_planilha)
self.interface_xml.setVisible(False)

main_layout.addWidget(self.container_dinamico)
```

### 3. Funções de Alternância

```python
def alternar_modo_fonte(self, modo):
    if modo == 'planilha':
        self.interface_planilha.setVisible(True)
        self.interface_xml.setVisible(False)
        self.modo_fonte = 'planilha'
    elif modo == 'xml':
        self.interface_planilha.setVisible(False)
        self.interface_xml.setVisible(True)
        self.modo_fonte = 'xml'
```

---

## 📊 Compatibilidade com Banco Existente

### Modo Append XML → SQLite

```python
# XMLs processados criam tabelas:
# - NFe (com estrutura fixa)
# - CTe (com estrutura fixa)

# Sistema de PK funciona igual:
# 1. Primeira vez: cria tabela com colunas definidas
# 2. Append: usa chave 'Chave NFe' ou 'Chave CTE'
# 3. Metadados salvos em _dataforge_metadata
```

---

## ✅ Checklist de Integração

### Funcionalidades Originais (Preservadas)
- [x] Seleção de arquivo Excel/CSV
- [x] Preview de dados
- [x] Detecção automática de tipos
- [x] Seleção manual de tipos
- [x] Checkboxes de chave primária
- [x] Normalização de nomes de colunas
- [x] Modo Novo Banco
- [x] Modo Anexar a Existente
- [x] Verificação de duplicatas
- [x] Sistema de metadados (_dataforge_metadata)
- [x] Progress bar
- [x] Console de logs
- [x] Botão guia de tipos
- [x] Reset automático
- [x] Dark theme

### Funcionalidades Novas (Adicionadas)
- [x] Radio buttons tipo de fonte
- [x] Processamento de XMLs (NFe/CTe)
- [x] Preview em abas (NFe | CTe)
- [x] Exportar XMLs para XLSX
- [x] Converter XMLs para SQLite
- [x] Detecção automática de tipo XML
- [x] Thread assíncrona para XML
- [x] Integração com sistema de PK

---

## 🎯 Vantagens da Arquitetura

1. **Zero Breaking Changes**: Código original 100% funcional
2. **Modular**: xml_processor.py separado
3. **Escalável**: Fácil adicionar novos tipos (JSON, Parquet, etc)
4. **Manutenível**: Lógica separada por tipo de fonte
5. **Testável**: Módulos independentes

---

## 📝 Próximos Passos

1. ✅ Criar `dataforge_pro_main.py` integrado
2. ✅ Manter `xml_processor.py` separado (já criado)
3. ✅ Atualizar `requirements.txt`
4. ✅ Testar fluxo completo
5. ✅ Documentar uso

---

<div align="center">

**Arquitetura Aprovada** ✅

*Mantém 100% das funcionalidades originais*  
*Adiciona suporte XML de forma não-invasiva*

</div>
