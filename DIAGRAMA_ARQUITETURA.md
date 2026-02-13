# 🏗️ DataForge Pro v2.0 - Diagrama de Arquitetura Visual

```
╔══════════════════════════════════════════════════════════════════════════╗
║                     DATAFORGE PRO v2.0 - UNIFIED                         ║
║              Conversor Universal: Excel/CSV/NFe/CTe → SQLite             ║
╚══════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│                          INTERFACE PRINCIPAL                              │
│                     (ResponsiveConverter - QWidget)                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Header: "DataForge Pro"                                         │   │
│  │  Subtitle: "XLSX/CSV/NFe/CTe para SQLite Engine"               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  TIPO DE FONTE:                                                  │   │
│  │   ○ Planilhas (Excel/CSV)     ○ XMLs Fiscais (NFe/CTe)        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │              CONTAINER DINÂMICO                                  │   │
│  │  ┌───────────────────┐      ┌──────────────────┐               │   │
│  │  │ Interface Planilha│      │ Interface XML    │               │   │
│  │  │ (ORIGINAL 100%)   │  OU  │ (NOVO)          │               │   │
│  │  │                   │      │                  │               │   │
│  │  │ • Sel. Arquivo    │      │ • Sel. Pasta     │               │   │
│  │  │ • Preview Tabela  │      │ • Tabs NFe/CTe   │               │   │
│  │  │ • Tipos + PKs     │      │ • Preview Dados  │               │   │
│  │  │ • Replace/Append  │      │ • Export/Convert │               │   │
│  │  └───────────────────┘      └──────────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  CONSOLE DE LOGS                                                 │   │
│  │  > Aguardando seleção...                                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  [████████████████████░░░░░] 80%  ← Progress Bar                        │
│                                                                           │
│  [  EXECUTAR CONVERSÃO  ]  ← Botão Principal                            │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘

                                    │
                                    │ Executa
                                    ▼

         ┌──────────────────────────────────────────────┐
         │         WORKERS (QThread)                     │
         ├──────────────────────────────────────────────┤
         │                                               │
         │  ┌─────────────────┐  ┌─────────────────┐   │
         │  │ ConversorWorker │  │   XMLWorker     │   │
         │  │ (Excel/CSV)     │  │   (NFe/CTe)     │   │
         │  ├─────────────────┤  ├─────────────────┤   │
         │  │ • Lê arquivo    │  │ • Escaneia pasta│   │
         │  │ • Normaliza     │  │ • Detecta tipo  │   │
         │  │ • Cria PK       │  │ • Processa XML  │   │
         │  │ • Verifica dup. │  │ • Extrai campos │   │
         │  │ • Converte tipos│  │ • Monta DataFr. │   │
         │  │ • Insere SQLite │  │ • Retorna dados │   │
         │  └─────────────────┘  └─────────────────┘   │
         │         │                      │             │
         │         │                      │             │
         └─────────┼──────────────────────┼─────────────┘
                   │                      │
                   ▼                      ▼

              ┌─────────┐          ┌─────────────┐
              │ SQLite  │          │ xml_processor│
              │ Database│          │    Module    │
              └─────────┘          └─────────────┘
                   │                      │
                   │                      ▼
                   │              ┌──────────────────┐
                   │              │ xml_extension.py │
                   │              │ • XMLWorker      │
                   │              │ • XMLPreview     │
                   │              │ • Export XLSX    │
                   │              │ • Convert SQLite │
                   │              └──────────────────┘
                   │
                   ▼
         
╔══════════════════════════════════════════════════════════╗
║               BANCO DE DADOS FINAL                       ║
╠══════════════════════════════════════════════════════════╣
║                                                           ║
║  Tabelas de Dados:                                       ║
║  ├─ Sheet1 (planilhas)                                   ║
║  ├─ Sheet2 (planilhas)                                   ║
║  ├─ NFe (XMLs)                                           ║
║  └─ CTe (XMLs)                                           ║
║                                                           ║
║  Tabela de Sistema:                                      ║
║  └─ _dataforge_metadata                                  ║
║      ├─ tabela: "Sheet1"                                 ║
║      ├─ colunas_pk: "Codigo,Data"                        ║
║      ├─ tabela: "NFe"                                    ║
║      ├─ colunas_pk: "Chave NFe"                          ║
║      └─ ...                                               ║
║                                                           ║
╚══════════════════════════════════════════════════════════╝
```

---

## 📦 Estrutura de Arquivos do Projeto

```
dataforge_pro_v2/
│
├── 📄 dataforge_pro_unified.py    ← ARQUIVO PRINCIPAL
│   ├── class ResponsiveConverter  ← Interface unificada
│   ├── class ConversorWorker      ← Thread Excel/CSV
│   ├── def setup_interface_planilha()
│   ├── def alternar_modo_fonte()
│   ├── def processar_xmls()
│   └── ... (todas as funções originais)
│
├── 📄 xml_processor.py            ← Processador XML
│   ├── class XMLProcessor
│   ├── def detect_xml_type()
│   ├── def process_nfe_file()
│   ├── def process_cte_file()
│   ├── def _extract_icms()
│   ├── def _extract_ipi()
│   └── ... (extração de impostos)
│
├── 📄 xml_extension.py            ← Extensão UI XML
│   ├── class XMLWorker(QThread)
│   ├── class XMLPreviewWidget
│   ├── def create_xml_interface()
│   └── ... (UI components)
│
├── 📄 requirements_v2.txt         ← Dependências
│
└── 📚 docs/
    ├── ARQUITETURA_INTEGRADA.md
    ├── GUIA_INTEGRACAO.md
    ├── XML_MODULE_DOCS.md
    ├── RESUMO_EXECUTIVO.md
    └── exemplos_uso.py
```

---

## 🔄 Fluxo de Dados Completo

### Modo Planilha (Original)

```
Usuário seleciona arquivo.xlsx
         │
         ▼
ResponsiveConverter.selecionar_excel()
         │
         ├─> Lê arquivo (dtype=str)
         ├─> Detecta tipos
         └─> Mostra preview
         │
         ▼
Usuário ajusta tipos e PKs
         │
         ▼
ResponsiveConverter.executar()
         │
         ├─> Cria ConversorWorker
         └─> worker.start()
         │
         ▼
ConversorWorker.run()
         │
         ├─> Normaliza colunas
         ├─> Cria _PK
         ├─> Verifica duplicatas (se append)
         ├─> Converte tipos
         └─> INSERT INTO SQLite
         │
         ▼
SQLite Database
         │
         └─> Tabelas + _dataforge_metadata
```

### Modo XML (Novo)

```
Usuário seleciona pasta XML
         │
         ▼
ResponsiveConverter.selecionar_pasta_xml()
         │
         └─> processar_xmls()
         │
         ▼
XMLWorker.run()
         │
         ├─> XMLProcessor.process_xml_folder()
         │   │
         │   ├─> Para cada arquivo .xml:
         │   │   ├─> Detecta tipo (NFe ou CTe)
         │   │   ├─> Parseia XML
         │   │   ├─> Extrai campos
         │   │   └─> Adiciona ao DataFrame
         │   │
         │   └─> Retorna (df_nfe, df_cte)
         │
         └─> Emite signal finalizado
         │
         ▼
ResponsiveConverter.xml_processado()
         │
         └─> XMLPreviewWidget.load_data()
         │
         ▼
Usuário escolhe ação:
         │
         ├─> Export XLSX → Excel com abas NFe/CTe
         │
         └─> Convert SQLite → Cria tabelas NFe/CTe
                               com _PK = Chave NFe/CTE
```

---

## 🎨 Interface Visual - Estados

### Estado 1: Inicial
```
┌────────────────────────────────┐
│ DataForge Pro                  │
│                                 │
│ Tipo: ● Planilhas  ○ XMLs     │
│                                 │
│ [Selecionar Arquivo]           │
│ Nenhum arquivo selecionado     │
│                                 │
│ Console: > Aguardando...        │
└────────────────────────────────┘
```

### Estado 2: Preview Planilha
```
┌────────────────────────────────┐
│ DataForge Pro                  │
│                                 │
│ Tipo: ● Planilhas  ○ XMLs     │
│                                 │
│ ┌────────────────────────────┐ │
│ │ PREVIEW                     │ │
│ │ Tipo → [TEXT▼] [INTEGER▼]  │ │
│ │ PK   → [✓]     [ ]          │ │
│ │ ────────────────────────    │ │
│ │ Linha 1 | abc   | 123       │ │
│ │ Linha 2 | def   | 456       │ │
│ └────────────────────────────┘ │
│                                 │
│ ○ Novo  ● Anexar               │
│                                 │
│ [EXECUTAR CONVERSÃO]           │
└────────────────────────────────┘
```

### Estado 3: Preview XML
```
┌────────────────────────────────┐
│ DataForge Pro                  │
│                                 │
│ Tipo: ○ Planilhas  ● XMLs     │
│                                 │
│ Pasta: /xmls/janeiro           │
│                                 │
│ ┌─ NFe ─┬─ CTe ────────────┐  │
│ │ 150 registros            │  │
│ │ ┌─────────────────────┐  │  │
│ │ │ Série | Nº NF | ... │  │  │
│ │ │ 001   | 123   | ... │  │  │
│ │ └─────────────────────┘  │  │
│ └──────────────────────────┘  │
│                                 │
│ [💾 XLSX] [🔄 SQLite]          │
└────────────────────────────────┘
```

---

## 🔐 Sistema de Chave Primária Unificado

### Planilhas
```python
# Usuário seleciona colunas
PK = Coluna1 + Coluna2 + ...

# Exemplo
Codigo | Data       → _PK
"ABC"  | "2024-01"  → "ABC|2024-01"
```

### XMLs
```python
# Automático baseado na chave fiscal

# NFe
_PK = Chave NFe (44 dígitos)

# CTe  
_PK = Chave CTE (44 dígitos)
```

### Metadados
```sql
CREATE TABLE _dataforge_metadata (
    tabela TEXT PRIMARY KEY,
    colunas_pk TEXT,
    data_criacao TEXT
);

-- Planilha
INSERT INTO _dataforge_metadata VALUES 
    ('Sheet1', 'Codigo,Data', '2024-02-13 10:30:00');

-- XML
INSERT INTO _dataforge_metadata VALUES 
    ('NFe', 'Chave NFe', '2024-02-13 10:35:00');
```

---

## ✅ Compatibilidade e Integração

### Backwards Compatible
- ✅ Código v1.0 funciona 100%
- ✅ Bancos existentes funcionam
- ✅ Nenhum usuário impactado

### Forward Compatible  
- ✅ Fácil adicionar novos formatos
- ✅ Estrutura escalável
- ✅ Módulos intercambiáveis

### Cross-Compatible
- ✅ Planilhas e XMLs no mesmo banco
- ✅ Sistema de PK unificado
- ✅ Metadados compartilhados

---

<div align="center">

## 🎉 Arquitetura Completa e Integrada

**Modular • Escalável • Não-Invasiva • Documentada**

</div>
