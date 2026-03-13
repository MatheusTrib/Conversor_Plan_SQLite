# DataForge Pro 🔥

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.0%2B-green)
![License](https://img.shields.io/badge/License-PolyForm-yellow)

**DataForge Pro** é uma ferramenta desktop para conversão de arquivos de planilhas (Excel/CSV) em bancos de dados SQLite, com recursos de normalização, detecção automática de tipos, gerenciamento de chaves primárias e prevenção de duplicidades.

---

## 📋 Índice

- [Características](#-características)
- [Objetivo do Projeto](#-objetivo-do-projeto)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Instalação](#-instalação)
- [Guia de Uso](#-guia-de-uso)
- [Funcionalidades Detalhadas](#-funcionalidades-detalhadas)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Casos de Uso](#-casos-de-uso)
- [Limitações Conhecidas](#-limitações-conhecidas)
- [Roadmap](#-roadmap)
- [Licença](#-licença)

---

## ✨ Características

### 🎯 Funcionalidades Principais

- ✅ **Conversão Multi-Formato**: Suporta `.xlsx`, `.xls`, `.xlsm` e `.csv`
- ✅ **Preview Inteligente**: Visualização de dados antes da conversão
- ✅ **Detecção Automática de Tipos**: Identifica automaticamente INTEGER, REAL, TEXT, DATE, DATETIME, etc.
- ✅ **Normalização de Nomes**: Remove acentos e caracteres especiais, substitui espaços por underscores
- ✅ **Chave Primária Composta**: Crie chaves únicas combinando múltiplas colunas
- ✅ **Prevenção de Duplicatas**: Sistema robusto de verificação com metadados persistentes
- ✅ **Processamento Assíncrono**: Interface responsiva durante conversões grandes
- ✅ **Logs Detalhados**: Acompanhamento completo do processo com console integrado
- ✅ **Interface Dark Theme**: Design moderno e profissional

### 🚀 Diferenciais Técnicos

- **Engine Calamine**: Leitura ultra-rápida de arquivos Excel
- **Leitura como String**: Preserva dados originais (IDs longos, números com zeros à esquerda)
- **Conversão Sob Demanda**: Tipos são convertidos apenas quando necessário
- **Sistema de Metadados**: Armazena informações de chaves primárias para integridade referencial
- **Modo Replace/Append**: Flexibilidade total para criar novos bancos ou anexar a existentes

---

## 🎯 Objetivo do Projeto

O **DataForge Pro** foi desenvolvido para resolver problemas comuns em análise de dados:

### Problema
Analistas e cientistas de dados frequentemente precisam:
- Converter planilhas Excel em bancos SQLite para análise
- Manter integridade dos dados (evitar duplicatas)
- Lidar com arquivos grandes sem travar a interface
- Preservar formatação de dados especiais (IDs, chaves)

### Solução
Uma ferramenta desktop que:
1. Automatiza a conversão com configurações inteligentes
2. Oferece controle fino sobre tipos de dados
3. Previne duplicatas através de chaves compostas
4. Mantém rastreabilidade completa do processo

### Público-Alvo
- Analistas de Dados
- Cientistas de Dados
- DBAs
- Desenvolvedores Python
- Profissionais de BI

---

## 🛠 Tecnologias Utilizadas

### Core
- **Python 3.8+**: Linguagem principal
- **PySide6**: Framework Qt para interface gráfica
- **pandas**: Manipulação e análise de dados
- **sqlite3**: Banco de dados embutido

### Bibliotecas Especializadas
- **calamine**: Engine de leitura rápida para Excel
- **xlrd**: Suporte para arquivos `.xls` legados
- **openpyxl**: Manipulação alternativa de Excel
- **unicodedata**: Normalização de caracteres Unicode

### Padrões e Arquitetura
- **MVC Pattern**: Separação clara entre modelo, visualização e controle
- **Threading**: QThread para operações assíncronas
- **Signals/Slots**: Comunicação entre threads
- **PRAGMA SQLite**: Otimizações de performance

---

## 📦 Instalação

### Requisitos do Sistema
- Python 3.8 ou superior
- 4GB RAM (recomendado 8GB para arquivos grandes)
- 100MB de espaço em disco

### Instalação via pip

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/dataforge-pro.git
cd dataforge-pro

# Crie um ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt
```

### Dependências (`requirements.txt`)

```
PySide6>=6.5.0
pandas>=2.0.0
openpyxl>=3.1.0
xlrd>=2.0.1
python-calamine>=0.1.7
```

### Execução

```bash
python dataforge_pro_enhanced.py
```

---

## 📖 Guia de Uso

### 1️⃣ Modo: Criar Novo Banco

#### Passo a Passo

**1. Selecione o Arquivo**
```
📁 Selecionar Arquivo → Escolha .xlsx, .xls, .csv ou .xlsm
```

**2. Revise o Preview**
- Sistema mostra primeiras 4 linhas
- Colunas normalizadas automaticamente
- Tipos detectados automaticamente

**3. Ajuste os Tipos (Opcional)**
- Clique no dropdown de cada coluna
- Escolha: TEXT, INTEGER, REAL, DATE, DATETIME, TIME, BOOLEAN, NUMERIC, BLOB

**4. Defina Chave Primária (Opcional)**
- Marque checkboxes das colunas que formam chave única
- Exemplo: `N_Documento` + `Material`
- Sistema criará coluna `_PK` automaticamente

**5. Execute**
```
EXECUTAR CONVERSÃO → Aguarde processamento → Banco criado!
```

#### Resultado
```
📁 minha_planilha.xlsx
    └─> 📊 minha_planilha.db
           └─> Tabela: Sheet1
                  ├─ N_Documento (TEXT)
                  ├─ Material (TEXT)
                  ├─ Quantidade (INTEGER)
                  └─ _PK (TEXT) → "12345|ABC123"
```

---

### 2️⃣ Modo: Anexar a Banco Existente

#### Passo a Passo

**1. Selecione o Arquivo Excel/CSV**

**2. Escolha "Anexar a Banco Existente"**
```
⚫ Novo Banco (.db)
🔘 Anexar a Banco Existente
```

**3. Selecione o Banco de Dados**
```
📂 Selecionar Banco Existente → Escolha .db existente
```

**4. Analise a Estrutura**
Sistema mostra automaticamente:
```
📊 Banco contém 1 tabela(s): Sheet1
  • Sheet1: N_Documento (TEXT), Material (TEXT), _PK (TEXT)
    🔑 PK formada por: N_Documento + Material
```

**5. Execute**
- ✅ Sistema usa estrutura existente
- ✅ Ignora configurações de tipo do preview
- ✅ Reconstrói `_PK` com mesmas colunas
- ✅ Filtra duplicatas automaticamente

#### Resultado
```
✓ Usando estrutura existente da tabela 'Sheet1'
  🔑 PK reconstruída: N_Documento + Material
⚠ 15 registros duplicados ignorados em 'Sheet1'
✓ 85 registros inseridos em 'Sheet1'
```

---

## 🔧 Funcionalidades Detalhadas

### 🧹 Normalização de Nomes de Colunas

#### O que faz
Converte nomes de colunas para formato compatível com SQL.

#### Regras
1. **Remove acentos**: `São Paulo` → `Sao Paulo`
2. **Substitui espaços**: `Data de Nascimento` → `Data_de_Nascimento`
3. **Remove caracteres especiais**: `Preço (R$)` → `Preco_R`

#### Exemplos
```python
"Número do Documento" → "Numero_do_Documento"
"Código@Fornecedor"   → "CodigoFornecedor"
"País de Origem"      → "Pais_de_Origem"
"% de Desconto"       → "de_Desconto"
```

---

### 🔍 Detecção Automática de Tipos

#### Algoritmo
O sistema analisa as primeiras 100 linhas e:

1. **INTEGER**: Se todos os valores são números inteiros
2. **REAL**: Se tem números com casas decimais
3. **DATE**: Se detecta padrão de data (YYYY-MM-DD)
4. **DATETIME**: Se detecta data + hora
5. **BOOLEAN**: Se apenas 2 valores únicos (true/false, 1/0, sim/não)
6. **TEXT**: Padrão para tudo que não se encaixa acima

#### Preservação de Dados
- ⚠️ **TODOS os dados são lidos como STRING inicialmente**
- ✅ Conversão acontece **APENAS** se você escolher tipo numérico
- ✅ IDs longos, chaves compostas, números com zeros à esquerda → **preservados**

---

### 🔑 Sistema de Chave Primária Composta

#### Como Funciona

**1. Criação**
```
Usuário marca: [✓] N_Documento  [✓] Material
                ↓
Sistema gera: _PK = "N_Documento|Material"
                ↓
Exemplo: _PK = "12345|ABC123"
```

**2. Armazenamento de Metadados**
```sql
CREATE TABLE _dataforge_metadata (
    tabela TEXT PRIMARY KEY,
    colunas_pk TEXT,
    data_criacao TEXT
)

INSERT INTO _dataforge_metadata VALUES 
    ('Sheet1', 'N_Documento,Material', '2024-02-10 14:30:00')
```

**3. Verificação de Duplicatas (Modo Append)**
```python
# Busca PKs existentes
pks_existentes = SELECT _PK FROM Sheet1

# Filtra novos dados
novos_dados = dados[~dados._PK.isin(pks_existentes)]

# Insere apenas não-duplicados
INSERT INTO Sheet1 VALUES (novos_dados)
```

#### Benefícios
- ✅ Garante unicidade de registros
- ✅ Funciona mesmo em bancos pré-existentes
- ✅ Rastreável através de metadados
- ✅ Suporta chaves compostas de N colunas

---

### ⚡ Otimizações de Performance

#### SQLite PRAGMA
```sql
PRAGMA synchronous = OFF      -- Desativa sync de disco (5x mais rápido)
PRAGMA journal_mode = MEMORY  -- Journal em memória (3x mais rápido)
```

#### Leitura Otimizada
- **Engine Calamine**: 10x mais rápido que openpyxl
- **Leitura como STRING**: Evita conversões desnecessárias
- **Chunking**: Insere em lotes de 15.000 registros

#### Threading
- **QThread**: Processamento em background
- **Signals**: Atualização de progresso sem travar UI
- **Progress Bar**: Feedback visual em tempo real

---

## 🏗 Arquitetura do Sistema

### Diagrama de Componentes

```
┌─────────────────────────────────────────────┐
│         ResponsiveConverter (UI)            │
│  ┌───────────────────────────────────────┐  │
│  │  - Seleção de arquivo                 │  │
│  │  - Preview de dados                   │  │
│  │  - Configuração de tipos              │  │
│  │  - Seleção de PK                      │  │
│  │  - Console de logs                    │  │
│  └───────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │ QThread.start()
                   ▼
┌─────────────────────────────────────────────┐
│       ConversorWorker (Processing)          │
│  ┌───────────────────────────────────────┐  │
│  │  1. Leitura de arquivo (dtype=str)    │  │
│  │  2. Normalização de colunas           │  │
│  │  3. Criação de _PK                    │  │
│  │  4. Verificação de duplicatas         │  │
│  │  5. Conversão de tipos                │  │
│  │  6. Inserção no SQLite                │  │
│  │  7. Salvamento de metadados           │  │
│  └───────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           SQLite Database                   │
│  ┌───────────────────────────────────────┐  │
│  │  - Tabelas de dados                   │  │
│  │  - _dataforge_metadata (sistema)      │  │
│  │  - Índices automáticos                │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

### Fluxo de Dados

```
Excel/CSV
    │
    ├─> [Leitura com dtype=str]
    │
    ├─> [DataFrame Pandas]
    │       │
    │       ├─> Normalização de colunas
    │       ├─> Criação de _PK (se configurado)
    │       ├─> Verificação de duplicatas (modo append)
    │       └─> Conversão de tipos
    │
    └─> [SQLite Database]
            ├─> Tabelas de dados
            └─> _dataforge_metadata
```

---

## 💼 Casos de Uso

### Caso 1: ETL de Notas Fiscais

**Cenário**: Empresa recebe planilhas mensais com 50.000 notas fiscais.

**Solução com DataForge Pro**:
1. **Mês 1**: Criar novo banco, definir PK = `N_Documento` + `Fornecedor`
2. **Mês 2+**: Anexar ao banco existente, sistema ignora duplicatas
3. **Resultado**: Base consolidada sem registros duplicados

**Economia**: ~80% de tempo vs. processo manual

---

### Caso 2: Análise de Dados de Pesquisa

**Cenário**: Pesquisador recebe respostas em CSV de múltiplas coletas.

**Solução com DataForge Pro**:
1. Converter cada CSV para SQLite
2. Tipos detectados automaticamente (idade=INTEGER, data=DATE)
3. Unificar em banco único para análise

**Benefício**: Consultas SQL vs. múltiplos CSVs

---

### Caso 3: Migração de Planilhas Legadas

**Cenário**: Sistema antigo exporta `.xls` com dados críticos.

**Solução com DataForge Pro**:
1. Suporte nativo a `.xls` (via xlrd)
2. Normalização automática de nomes "problemáticos"
3. Preservação de IDs longos e códigos especiais

**Garantia**: Integridade 100% dos dados

---

## ⚠️ Limitações Conhecidas

### 1. Formatos de Arquivo
- ❌ **Não suporta**: `.ods` (LibreOffice), Google Sheets diretamente
- ✅ **Solução**: Exportar para `.xlsx` ou `.csv` antes

### 2. Tamanho de Arquivo
- ⚠️ **Recomendado**: Até 500MB por arquivo
- ⚠️ **Memória**: Arquivo carregado completamente em RAM
- ✅ **Otimização**: Usar chunking para arquivos >1GB (próxima versão)

### 3. Tipos de Dados
- ⚠️ **SQLite não tem tipo DATE nativo**: Armazenado como TEXT ISO8601
- ⚠️ **BLOB**: Dados binários não são testados extensivamente
- ✅ **Conversão**: Sempre possível converter TEXT→DATE nas queries

### 4. Chave Primária
- ⚠️ **Reconstrução automática limitada**: Em bancos sem metadados
- ⚠️ **Ordem importa**: Colunas devem estar na mesma ordem
- ✅ **Solução**: Sempre use metadados (padrão em novas criações)

### 5. Interface
- ⚠️ **Monitoramento**: Mostra apenas primeira aba no preview
- ⚠️ **Multi-sheet**: Todas as abas são processadas, mas preview é limitado
- ✅ **Logs**: Console mostra progresso de todas as abas

---

## 🗺 Roadmap

### v2.0 (Próxima Release)
- [ ] Suporte a Google Sheets API
- [ ] Modo incremental (apenas linhas novas)
- [ ] Export reverso (SQLite → Excel)
- [ ] Agendamento de conversões
- [ ] CLI (Command Line Interface)

### v2.5
- [ ] Suporte a PostgreSQL/MySQL
- [ ] Validação de dados (regex patterns)
- [ ] Transformações customizadas (scripts Python)
- [ ] Compressão de banco de dados

### v3.0
- [ ] Interface web (FastAPI + React)
- [ ] Suporte multi-usuário
- [ ] Histórico de conversões
- [ ] API REST

---

## 📄 Licença

Este projeto está licenciado sob a **PolyForm Noncommercial**.

```
# PolyForm Noncommercial License 1.0.0

<https://polyformproject.org/licenses/noncommercial/1.0.0>

## Acceptance

In order to get any license under these terms, you must agree
to them as both strict obligations and conditions to all
your licenses.

## Copyright License

The licensor grants you a copyright license for the
software to do everything you might do with the software
that would otherwise infringe the licensor's copyright
in it for any permitted purpose.  However, you may
only distribute the software according to [Distribution
License](#distribution-license) and make changes or new works
based on the software according to [Changes and New Works
License](#changes-and-new-works-license).

## Distribution License

The licensor grants you an additional copyright license
to distribute copies of the software.  Your license
to distribute covers distributing the software with
changes and new works permitted by [Changes and New Works
License](#changes-and-new-works-license).

## Notices

You must ensure that anyone who gets a copy of any part of
the software from you also gets a copy of these terms or the
URL for them above, as well as copies of any plain-text lines
beginning with `Required Notice:` that the licensor provided
with the software.  For example:

> Required Notice: Copyright Yoyodyne, Inc. (http://example.com)

## Changes and New Works License

The licensor grants you an additional copyright license to
make changes and new works based on the software for any
permitted purpose.

## Patent License

The licensor grants you a patent license for the software that
covers patent claims the licensor can license, or becomes able
to license, that you would infringe by using the software.

## Noncommercial Purposes

Any noncommercial purpose is a permitted purpose.

## Personal Uses

Personal use for research, experiment, and testing for
the benefit of public knowledge, personal study, private
entertainment, hobby projects, amateur pursuits, or religious
observance, without any anticipated commercial application,
is use for a permitted purpose.

## Noncommercial Organizations

Use by any charitable organization, educational institution,
public research organization, public safety or health
organization, environmental protection organization,
or government institution is use for a permitted purpose
regardless of the source of funding or obligations resulting
from the funding.

## Fair Use

You may have "fair use" rights for the software under the
law. These terms do not limit them.

## No Other Rights

These terms do not allow you to sublicense or transfer any of
your licenses to anyone else, or prevent the licensor from
granting licenses to anyone else.  These terms do not imply
any other licenses.

## Patent Defense

If you make any written claim that the software infringes or
contributes to infringement of any patent, your patent license
for the software granted under these terms ends immediately. If
your company makes such a claim, your patent license ends
immediately for work on behalf of your company.

## Violations

The first time you are notified in writing that you have
violated any of these terms, or done anything with the software
not covered by your licenses, your licenses can nonetheless
continue if you come into full compliance with these terms,
and take practical steps to correct past violations, within
32 days of receiving notice.  Otherwise, all your licenses
end immediately.

## No Liability

***As far as the law allows, the software comes as is, without
any warranty or condition, and the licensor will not be liable
to you for any damages arising out of these terms or the use
or nature of the software, under any kind of legal claim.***

## Definitions

The **licensor** is the individual or entity offering these
terms, and the **software** is the software the licensor makes
available under these terms.

**You** refers to the individual or entity agreeing to these
terms.

**Your company** is any legal entity, sole proprietorship,
or other kind of organization that you work for, plus all
organizations that have control over, are under the control of,
or are under common control with that organization.  **Control**
means ownership of substantially all the assets of an entity,
or the power to direct its management and policies by vote,
contract, or otherwise.  Control can be direct or indirect.

**Your licenses** are all the licenses granted to you for the
software under these terms.

**Use** means anything you do with the software requiring one
of your licenses.
```

---

## 📊 Estatísticas do Projeto

- **Linhas de Código**: ~1000
- **Funções**: 35+
- **Classes**: 2 principais
- **Tipos SQLite Suportados**: 9
- **Formatos de Arquivo**: 4

---

## 🔗 Links Úteis

- [Documentação SQLite](https://www.sqlite.org/docs.html)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
- [Python Calamine](https://pypi.org/project/python-calamine/)

---

<div align="center">

**⭐ Se este projeto foi útil, considere dar uma estrela no GitHub! ⭐**

![Made with Love](https://img.shields.io/badge/Made%20with-❤️-red)
![Python](https://img.shields.io/badge/Made%20with-Python-blue)

</div>
