# 🐍 ast_parser.py — Python AST Parser

> **Location**: `backend/app/code_parsing/ast_parser.py`
> **Purpose**: Parse Python source files using Python's built-in `ast` module and extract functions, classes, imports, calls, variables, and security flags.

---

## What Does It Do?

This module takes a **Python source code string** and returns a **structured dictionary** describing everything interesting about the file — every function, class, import, function call, module-level variable, and any security-relevant patterns it detects.

It uses Python's built-in `ast` (Abstract Syntax Tree) module, which means it can perfectly parse any valid Python syntax.

---

## Public API

### `parse_python_file(filepath: str, source: str) → dict`

**Inputs**:
- `filepath` — Relative path of the file (for display only — **does not read from disk**)
- `source` — Raw UTF-8 source code string (from `file_reader.py`)

**Output**: A structured dict. Here's an example:

```json
{
  "filepath": "src/auth.py",
  "language": "python",
  "parse_error": null,
  "functions": [
    {
      "name": "login",
      "line_start": 10,
      "line_end": 25,
      "args": ["self", "user", "pwd"],
      "is_async": false,
      "decorators": ["app.route"],
      "calls_made": ["os.system", "eval", "db.query"]
    }
  ],
  "classes": [
    {
      "name": "AuthService",
      "line_start": 5,
      "line_end": 40,
      "base_classes": ["BaseService"],
      "methods": ["login", "logout", "verify"]
    }
  ],
  "imports": [
    {
      "module": "flask",
      "names": ["request", "jsonify"],
      "alias": [],
      "line": 1,
      "is_from_import": true
    }
  ],
  "calls": [
    {
      "caller_function": "login",
      "callee": "os.system",
      "line": 15,
      "args_count": 1
    }
  ],
  "module_variables": [
    {
      "name": "SECRET_KEY",
      "line": 3,
      "has_string_value": true
    }
  ],
  "security_flags": {
    "uses_eval": true,
    "uses_exec": false,
    "uses_os_system": true,
    "uses_subprocess": false,
    "uses_pickle": false,
    "has_sql_string": true,
    "has_hardcoded_str": true
  },
  "stats": {
    "total_functions": 3,
    "total_classes": 1,
    "total_imports": 5,
    "total_calls": 12,
    "lines_of_code": 85
  }
}
```

---

## How It Works — The `_CodeVisitor`

The core of this module is the **`_CodeVisitor`** class, which extends Python's `ast.NodeVisitor`. It does a **single pass** over the AST tree and populates extraction buckets as it encounters different node types.

### Visitor Pattern Explained

The AST visitor pattern works like this:

1. Python's `ast.parse(source)` turns source code into a tree of nodes
2. `_CodeVisitor` walks the tree, and when it encounters a node of type `X`, it calls `visit_X(node)`
3. Each `visit_X` method extracts the relevant information and stores it

```
Source Code → ast.parse() → AST Tree → _CodeVisitor.visit() → Structured Data
```

### What Gets Visited

| AST Node Type | Visitor Method | What It Extracts |
|---------------|----------------|------------------|
| `Import` | `visit_Import` | Module names, aliases, subprocess/pickle flags |
| `ImportFrom` | `visit_ImportFrom` | Module, imported names, aliases |
| `FunctionDef` | `visit_FunctionDef` | Name, args, line range, decorators, calls made |
| `AsyncFunctionDef` | `visit_AsyncFunctionDef` | Same as above, with `is_async: true` |
| `ClassDef` | `visit_ClassDef` | Name, base classes, method names |
| `Call` | `visit_Call` | Caller function, callee name, line, arg count |
| `Assign` | `visit_Assign` | Module-level variable names, string value check |
| `AnnAssign` | `visit_AnnAssign` | Same as Assign but for annotated assignments |
| `Constant` | `visit_Constant` | SQL keyword detection in string literals |

---

## Security Flags — What Gets Flagged

The parser detects 7 security-relevant patterns:

| Flag | What Triggers It | Why It Matters |
|------|-----------------|----------------|
| `uses_eval` | A call to `eval()` anywhere in the file | Code injection risk |
| `uses_exec` | A call to `exec()` | Code injection risk |
| `uses_os_system` | A call to `os.system()` | Command injection risk |
| `uses_subprocess` | Importing the `subprocess` module | Potential command injection |
| `uses_pickle` | Importing the `pickle` module | Deserialization attacks |
| `has_sql_string` | Any string containing `SELECT`, `INSERT`, `UPDATE`, or `DELETE` | Potential SQL injection |
| `has_hardcoded_str` | Module-level variable assigned a string literal | Potential hardcoded secrets |

> **Important**: These are **heuristic flags**, not definitive vulnerabilities. The LLM agent uses them alongside Semgrep findings to make a final judgment.

---

## Scope Tracking

The visitor maintains a **scope stack** to track which function the code is currently inside:

```python
self._scope_stack: list[str] = ["module_level"]
```

- When entering a function: pushes the function name onto the stack
- When leaving a function: pops it off
- The `visit_Call` method reads the current scope to record which function made the call

This is how the parser knows that `eval()` was called **inside** `login()` rather than at the module level.

```python
# scope_stack = ["module_level"]
def login(user):          # push → ["module_level", "login"]
    eval(user)            # caller_function = "login"
                          # pop  → ["module_level"]

eval("something")         # caller_function = "module_level"
```

---

## Call Name Resolution

The `_resolve_call_name()` helper converts AST call nodes into human-readable dotted names:

| AST Pattern | Resolved Name |
|-------------|---------------|
| `eval(x)` | `"eval"` |
| `os.system(cmd)` | `"os.system"` |
| `self.save()` | `"self.save"` |
| `cursor.execute(q)` | `"cursor.execute"` |
| `a.b.c.d()` | `"a.b.c.d"` |
| Complex expression | `"<complex>"` |

---

## Error Handling

The function **never raises**. Instead:

| Error | Behavior |
|-------|----------|
| `SyntaxError` in source | Returns `_empty_result()` with `parse_error` set |
| Unexpected parse error | Returns `_empty_result()` with `parse_error` set |
| Unexpected visitor error | Returns `_empty_result()` with `parse_error` set |

The `_empty_result()` function returns a valid dict with all lists empty and all flags `False`.

---

## Module-Level Variables

The parser captures variables defined at the **top level** of the file (not inside functions or classes):

```python
# These ARE captured:
SECRET_KEY = "hunter2"        # has_string_value: true
DB_URL: str = "postgres://..."  # has_string_value: true (annotated assignment)
MAX_RETRIES = 3               # has_string_value: false

# These are NOT captured (inside functions):
def foo():
    local_var = "not captured"
```

---

## Internal Flow

```
parse_python_file(filepath, source)
    │
    ├── Count lines_of_code
    │
    ├── ast.parse(source) → tree
    │     └── On SyntaxError → return _empty_result()
    │
    ├── _CodeVisitor().visit(tree)
    │     ├── visit_Import / visit_ImportFrom → imports[], subprocess/pickle flags
    │     ├── visit_FunctionDef → functions[], push/pop scope
    │     ├── visit_ClassDef → classes[]
    │     ├── visit_Call → calls[], eval/exec/os.system flags
    │     ├── visit_Assign / visit_AnnAssign → module_variables[], hardcoded_str flag
    │     └── visit_Constant → SQL string detection
    │
    └── Return structured dict
```
