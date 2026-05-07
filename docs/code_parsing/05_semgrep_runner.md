# Semgrep Runner (`semgrep_runner.py`)

This document describes the `semgrep_runner.py` module, which integrates the Semgrep static analysis tool into the Vulture pipeline to identify security vulnerabilities and code quality issues.

## Overview

While the AST and Tree-sitter parsers extract structural information and basic heuristics, Semgrep provides deep, pattern-based static analysis. This module wraps the Semgrep CLI, executes it against the codebase, and processes its output into a format suitable for the rest of the pipeline.

## Execution Workflow

### 1. Subprocess Execution
The module executes Semgrep as a subprocess.
- It invokes the `semgrep` CLI command.
- It configures Semgrep to run with specific rule sets (e.g., standard security rules, specific language rules) using command-line arguments.
- It directs Semgrep to output results in JSON format.

### 2. JSON Parsing
Once the Semgrep subprocess completes, the module captures its standard output.
- It parses the JSON output string into Python dictionaries.
- It handles potential execution errors or invalid JSON output gracefully, adhering to the pipeline's "never-raise" policy to ensure orchestration continues even if scanning fails.

### 3. Finding Deduplication
Semgrep can sometimes report duplicate findings or multiple findings that point to the exact same issue on the same line.
- The module implements a deduplication step to clean up the results.
- It groups findings by file path, line number, and rule ID, keeping only unique instances to reduce noise.

### 4. Severity Mapping
Semgrep reports findings with its own severity levels (e.g., `ERROR`, `WARNING`, `INFO`).
- The `semgrep_runner` maps these Semgrep-specific severities into a standard Vulture severity scale used by the LLM agent and frontend.
- It translates Semgrep rule metadata into a standardized vulnerability format.

## Integration in the Pipeline

The Semgrep runner operates in parallel with the code parsing phase within the `orchestrator`'s LangGraph DAG. Its findings are eventually merged with the structural data (call graph, security flags) during the fan-in stage, providing a comprehensive context for the final LLM analysis.
