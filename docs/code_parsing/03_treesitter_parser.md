# Tree-sitter Parser (`treesitter_parser.py`)

This document outlines the architecture and workflow of the `treesitter_parser.py` module, which handles the parsing of non-Python files using the Tree-sitter library.

## Overview

While Python files are parsed using the built-in `ast` module, other supported languages (e.g., JavaScript, TypeScript, Java, C++) are parsed using Tree-sitter. This module acts as an adapter, translating the diverse syntax trees of various languages into a unified data schema that the rest of the Vulture pipeline can understand.

## Key Concepts

### 1. Lazy Grammar Registry
To avoid long startup times and unnecessary memory consumption, Tree-sitter language grammars are loaded **lazily**. 
- Grammars are only compiled and loaded when a file of that specific language is first encountered.
- Once loaded, the grammar is cached in a registry for subsequent uses.

### 2. The `_Extractor` Walker
The core of the parsing logic is the `_Extractor` class. It walks the Tree-sitter syntax tree to extract relevant information.
- It maps language-specific node types (e.g., `function_declaration` in JS, `MethodDeclaration` in Java) to a standard set of concepts (classes, functions, calls).
- It traverses the tree recursively, maintaining context to properly scope variables and function definitions.

## Output Schema Uniformity

The most critical design principle of this module is **Schema Uniformity**. 
Regardless of the input language, the `treesitter_parser` outputs a dictionary identical in structure to the one produced by `ast_parser.py`. This ensures that downstream modules (like `call_graph` and `orchestrator`) do not need language-specific branching logic.

The unified schema includes:
- `symbols`: Defined classes and functions.
- `calls`: Function calls made within the file.
- `imports`: Dependencies imported by the file.
- `security_flags`: Contextual security heuristics.

## Workflow

1.  **Language Detection**: Based on the file extension, the appropriate Tree-sitter grammar is identified.
2.  **Lazy Loading**: If the grammar is not yet loaded, it is compiled and loaded into the registry.
3.  **Tree Parsing**: The file content is parsed using the Tree-sitter parser configured with the loaded grammar, resulting in a syntax tree.
4.  **Extraction**: The `_Extractor` walks the syntax tree, identifying symbols, calls, and imports according to language-specific rules but mapping them to the unified schema.
5.  **Return**: A standardized dictionary containing the extracted information is returned.
