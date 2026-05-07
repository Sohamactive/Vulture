# Important Notes & Design Constraints

This document highlights critical design decisions, constraints, and operational philosophies that govern the `code_parsing` module. Adhering to these principles is crucial for maintaining system stability, performance, and security.

## 1. No File Writes (Read-Only Policy)

The entire code parsing pipeline (`file_reader`, parsers, `call_graph`, `semgrep_runner`) is strictly **read-only** with respect to the user's repository.
- **No Side Effects**: The system must never modify, delete, or create files within the scanned codebase.
- **Temporary Files**: If temporary files are needed (e.g., for specific Semgrep configs), they must be created in the system's temporary directory (`/tmp` or `%TEMP%`) and cleaned up immediately, never inside the target repository.

## 2. No LLM Calls During Parsing

The parsing phase is purely deterministic and relies solely on static analysis (AST, Tree-sitter, Semgrep).
- **Performance**: Making LLM API calls per file or per function during the initial scan would be prohibitively slow and expensive.
- **Separation of Concerns**: The parsing modules gather facts and build the context. The LLM agent is invoked *later* in the pipeline, utilizing this aggregated context to perform high-level reasoning and vulnerability verification.

## 3. The "Never-Raise" Policy

The pipeline is designed to be highly resilient. Individual file parsing failures or localized errors should not crash the entire scan.
- **Graceful Degradation**: Parsers and runners wrap their core logic in `try...except` blocks.
- **Error Logging**: Errors are logged or appended to the `ScanState`'s `errors` list for later review, but the execution continues.
- **Partial Results**: It is better to return partial data (e.g., a call graph missing one malformed file) than to fail the entire operation.

## 4. Pure Python Backend

The backend orchestration and parsing logic is implemented in pure Python (utilizing C-extensions like `tree-sitter` internally, but exposed via Python APIs).
- This ensures portability and simplifies deployment.
- System-level dependencies are minimized (except for the `semgrep` binary, which is required).

## 5. Stateless Operation

Modules like `ast_parser`, `treesitter_parser`, and `semgrep_runner` should be effectively stateless between different files or scan runs.
- They take input (file path/content) and return output (parsed dictionary) without maintaining internal state that could bleed across parallel executions.
- All state management is centralized within the `ScanState` handled by `langgraph` in the `orchestrator`.
