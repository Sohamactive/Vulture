# Call Graph Builder (`call_graph.py`)

This document explains the `call_graph.py` module, which is responsible for taking the individual parsed file outputs and constructing a repository-wide view of dependencies and function calls.

## Overview

The Call Graph builder aggregates the isolated, file-level parsing results into a unified, cross-file relationship map. This is essential for understanding the overall architecture of the codebase and tracing the flow of execution or data between different components.

## Core Processes

### 1. Symbol Table Construction
The first step is building a global symbol table. 
- It iterates through the parsed output of every file.
- It registers every defined class, function, and method along with its source file and location.
- This creates a lookup table allowing the system to resolve where a called function is actually defined.

### 2. Dependency & Call Graph Generation
Once the symbol table is built, the module constructs the graphs:
-   **Import Graph**: Maps which files depend on which other files based on extracted import statements.
-   **Call Graph**: Maps which functions call which other functions. It uses the symbol table to resolve local calls (within the same file) and cross-file calls.

### 3. Cycle Detection (DFS)
The module includes logic to detect cycles in the import graph using Depth-First Search (DFS).
- Identifying circular dependencies is crucial for understanding potential architectural issues or areas where refactoring might be needed.

### 4. Hotspot Analysis Logic
The graph structure allows for hotspot analysis.
- By analyzing the in-degree (how many times a function is called) and out-degree (how many functions it calls) of nodes in the call graph, the system can identify "hotspots" or highly central components in the codebase.
- These hotspots are often critical areas for security review or performance optimization.

## Data Consistency

The `call_graph.py` module expects the input data to strictly adhere to the unified schema produced by both `ast_parser.py` and `treesitter_parser.py`. It treats all languages agnostically, relying purely on the standardized symbols, calls, and imports data structures.
