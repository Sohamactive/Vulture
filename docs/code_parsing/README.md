# 📂 Code Parsing Module — Full Documentation

> **Location**: `backend/app/code_parsing/`
> **Purpose**: Read a codebase, parse every source file into a structured format, detect security flags, build a cross-file call graph, and run Semgrep security scans — all feeding into the LLM vulnerability agent.

---

## What is this module?

The `code_parsing` package is the **core analysis engine** of Vulture. It takes a raw repository path on disk and produces rich, structured data about every file — functions, classes, imports, call relationships, and security red flags. This structured data is then consumed by the LLM agent to generate vulnerability reports.

Think of it as a **multi-stage pipeline**:

```
Repository on Disk
       │
       ▼
  ┌────────────┐
  │ file_reader │  ← Reads & filters all relevant files
  └─────┬──────┘
        │
   ┌────┴────┐
   ▼         ▼
┌──────┐  ┌───────────┐
│ AST  │  │ Treesitter │  ← Parses every source file
│Parser│  │  Parser    │
└──┬───┘  └─────┬─────┘
   │            │
   └─────┬──────┘
         ▼
  ┌─────────────┐
  │  call_graph  │  ← Builds cross-file relationships
  └──────┬──────┘
         │
         ▼
  ┌──────────────┐
  │ semgrep_runner│  ← Runs security scan (parallel)
  └──────────────┘
```

---

## Module Files at a Glance

| File | Purpose | Lines |
|------|---------|-------|
| [`file_reader.py`](./01_file_reader.md) | Walks the repo, reads files, returns raw content | ~188 |
| [`ast_parser.py`](./02_ast_parser.md) | Parses Python files using the `ast` module | ~394 |
| [`treesitter_parser.py`](./03_treesitter_parser.md) | Parses JS/TS/Go/Java/Rust/etc. using Tree-sitter | ~700 |
| [`call_graph.py`](./04_call_graph.md) | Builds symbol table, import graph, call edges | ~444 |
| [`semgrep_runner.py`](./05_semgrep_runner.md) | Runs Semgrep CLI and parses JSON findings | ~242 |
| `chunk_extractor.py` | Placeholder for future chunk-based extraction | Empty |
| `__init__.py` | Package marker | Empty |

---

## How It Fits Into Vulture

The `code_parsing` module is **consumed exclusively** by the orchestrator (`app/agents/orchestrator.py`), which wires all modules into a **LangGraph DAG** (Directed Acyclic Graph). The user never calls these modules directly — the orchestrator handles everything.

```
User → API endpoint → orchestrator.start_scan() → code_parsing modules → LLM Agent → Report
```

---

## Documentation Index

| Document | What You'll Learn |
|----------|-------------------|
| [**Workflow**](./00_workflow.md) | End-to-end pipeline, how data flows between modules |
| [**file_reader.py**](./01_file_reader.md) | How files are discovered, filtered, and read |
| [**ast_parser.py**](./02_ast_parser.md) | Python-specific AST parsing, security flag detection |
| [**treesitter_parser.py**](./03_treesitter_parser.md) | Multi-language parsing with Tree-sitter |
| [**call_graph.py**](./04_call_graph.md) | Cross-file symbol resolution, import graph, hotspots |
| [**semgrep_runner.py**](./05_semgrep_runner.md) | Running Semgrep, parsing findings, deduplication |
| [**Data Structures**](./06_data_structures.md) | Every dict/schema used across the pipeline |
| [**Important Notes**](./07_important_notes.md) | Error handling, constraints, gotchas |

---

## Quick Start (for developers)

```python
# 1. Read all files from a repo
from app.code_parsing.file_reader import read_codebase
codebase = read_codebase("/path/to/repo")

# 2. Parse each file
from app.code_parsing.ast_parser import parse_python_file
from app.code_parsing.treesitter_parser import parse_file

results = []
for filepath, source in codebase["files"].items():
    if filepath.endswith(".py"):
        results.append(parse_python_file(filepath, source))
    else:
        results.append(parse_file(filepath, source))

# 3. Build the call graph
from app.code_parsing.call_graph import build_call_graph
graph = build_call_graph(results)

# 4. Run Semgrep
from app.code_parsing.semgrep_runner import run_semgrep
findings = run_semgrep("/path/to/repo")
```

> **Note**: In production, you don't call these directly. The orchestrator does it for you via `start_scan()`.
