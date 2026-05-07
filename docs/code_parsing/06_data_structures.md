# Data Structures (`data_structures.md`)

This document serves as a reference for the core JSON schemas and data structures used throughout the `code_parsing` module. Ensuring these structures remain consistent is vital for the pipeline's stability.

## 1. Unified Parse Result Schema

This dictionary structure is returned by **both** `ast_parser.py` and `treesitter_parser.py` for every file parsed.

```json
{
  "file_path": "string",
  "language": "string",
  "symbols": [
    {
      "name": "string",
      "type": "class|function|method",
      "line_start": "integer",
      "line_end": "integer",
      "complexity": "integer (optional)"
    }
  ],
  "calls": [
    {
      "caller": "string (symbol name or 'global')",
      "callee": "string (function name called)",
      "line": "integer"
    }
  ],
  "imports": [
    {
      "module": "string",
      "alias": "string (optional)",
      "line": "integer"
    }
  ],
  "security_flags": [
    "string (e.g., 'uses_eval', 'has_sql_string')"
  ]
}
```

## 2. Call Graph Node Schema

Representing nodes within the `call_graph.py` output.

```json
{
  "id": "string (unique identifier, e.g., 'file.py:FunctionName')",
  "type": "function|class",
  "file": "string",
  "in_degree": "integer",
  "out_degree": "integer"
}
```

## 3. Semgrep Finding Schema

The standardized output produced by `semgrep_runner.py` after parsing the raw Semgrep JSON.

```json
{
  "file": "string",
  "line": "integer",
  "rule_id": "string",
  "message": "string",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
  "code_snippet": "string"
}
```

## 4. Orchestrator ScanState

The central state object managed by `langgraph` in `orchestrator.py`.

```python
class ScanState(TypedDict):
    scan_id: str
    target_dir: str
    files_to_parse: List[str]
    parsed_data: Dict[str, dict]  # Key: file_path, Value: Unified Parse Result
    semgrep_findings: List[dict]  # List of Semgrep Finding Schema
    call_graph: dict
    errors: List[str]
    status: str
```
