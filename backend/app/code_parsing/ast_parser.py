import ast
from typing import Any

try:
    from app.logger import get_logger
except ImportError:
    # Fallback when run directly as a script (sys.path lacks the backend/ root)
    import logging as _logging
    def get_logger(name: str) -> _logging.Logger:  # type: ignore[misc]
        return _logging.getLogger(name)

logger = get_logger(__name__)

# SQL DML keywords for has_sql_string detection
_SQL_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_call_name(node: ast.expr) -> str:
    """
    Resolve an AST call target to a human-readable dotted name.

    Examples:
      ast.Name  → "eval", "print"
      ast.Attribute → "os.system", "cursor.execute", "self.save"
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _resolve_call_name(node.value)
        return f"{prefix}.{node.attr}"
    # Subscript, call-on-call, etc. — best-effort
    return "<complex>"


def _decorator_name(node: ast.expr) -> str:
    """Return a decorator's display name."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _resolve_call_name(node)
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return "<decorator>"


def _arg_names(args: ast.arguments) -> list[str]:
    """Extract all argument names from an ast.arguments node."""
    all_args = (
        args.posonlyargs
        + args.args
        + args.kwonlyargs
        + ([args.vararg] if args.vararg else [])
        + ([args.kwarg] if args.kwarg else [])
    )
    return [a.arg for a in all_args]


# ---------------------------------------------------------------------------
# Core visitor
# ---------------------------------------------------------------------------

class _CodeVisitor(ast.NodeVisitor):
    """
    Single-pass AST visitor that populates all extraction buckets.
    """

    def __init__(self) -> None:
        # Extraction buckets
        self.functions: list[dict] = []
        self.classes: list[dict] = []
        self.imports: list[dict] = []
        self.calls: list[dict] = []
        self.module_variables: list[dict] = []

        # Security flags
        self.uses_eval = False
        self.uses_exec = False
        self.uses_os_system = False
        self.uses_subprocess = False
        self.uses_pickle = False
        self.has_sql_string = False
        self.has_hardcoded_str = False

        # Context stack: tracks which function scope we are currently inside.
        # "module_level" when at the top of the module.
        self._scope_stack: list[str] = ["module_level"]

    # --- helpers ---

    @property
    def _current_scope(self) -> str:
        return self._scope_stack[-1]

    def _calls_made_in(self, node: ast.AST) -> list[str]:
        """Return deduplicated list of call names directly inside a function body."""
        names = []
        seen: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = _resolve_call_name(child.func)
                if name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def _check_string_for_sql(self, value: str) -> None:
        upper = value.upper()
        if any(kw in upper for kw in _SQL_KEYWORDS):
            self.has_sql_string = True

    # --- visitor methods ---

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "names": [],
                "alias": [alias.asname] if alias.asname else [],
                "line": node.lineno,
                "is_from_import": False,
            })
            mod_root = alias.name.split(".")[0]
            if mod_root == "subprocess":
                self.uses_subprocess = True
            if mod_root == "pickle":
                self.uses_pickle = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        names = [a.name for a in node.names]
        aliases = [a.asname for a in node.names if a.asname]
        self.imports.append({
            "module": module,
            "names": names,
            "alias": aliases,
            "line": node.lineno,
            "is_from_import": True,
        })
        mod_root = module.split(".")[0]
        if mod_root == "subprocess":
            self.uses_subprocess = True
        if mod_root == "pickle":
            self.uses_pickle = True
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        func_name = node.name
        calls_made = self._calls_made_in(node)  # for the functions[] bucket only

        self.functions.append({
            "name": func_name,
            "line_start": node.lineno,
            "line_end": node.end_lineno,
            "args": _arg_names(node.args),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "decorators": [_decorator_name(d) for d in node.decorator_list],
            "calls_made": calls_made,
        })

        self._scope_stack.append(func_name)
        self.generic_visit(node)  # NodeVisitor walks children — visit_Call fires per call
        self._scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        base_classes = [_resolve_call_name(base) for base in node.bases]

        # Direct methods only (one level deep — nested classes handled by generic_visit)
        methods = [
            n.name
            for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

        self.classes.append({
            "name": node.name,
            "line_start": node.lineno,
            "line_end": node.end_lineno,
            "base_classes": base_classes,
            "methods": methods,
        })
        self.generic_visit(node)

    # Module-level call nodes (not inside any function)
    def visit_Call(self, node):
        callee = _resolve_call_name(node.func)
        self.calls.append({
            "caller_function": self._current_scope,  # works for both module_level and functions
            "callee": callee,
            "line": node.lineno,
            "args_count": len(node.args) + len(node.keywords),
        })
        # security flags
        if callee == "eval": self.uses_eval = True
        if callee == "exec": self.uses_exec = True
        if callee == "os.system": self.uses_os_system = True
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._current_scope != "module_level":
            self.generic_visit(node)
            return
        for target in node.targets:
            if isinstance(target, ast.Name):
                is_str = isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                if is_str:
                    self.has_hardcoded_str = True
                    self._check_string_for_sql(node.value.value)
                self.module_variables.append({
                    "name": target.id,
                    "line": node.lineno,
                    "has_string_value": is_str,
                })
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._current_scope != "module_level":
            self.generic_visit(node)
            return
        if isinstance(node.target, ast.Name) and node.value is not None:
            is_str = isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
            if is_str:
                self.has_hardcoded_str = True
                self._check_string_for_sql(node.value.value)
            self.module_variables.append({
                "name": node.target.id,
                "line": node.lineno,
                "has_string_value": is_str,
            })
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        """Catch SQL strings anywhere in the file."""
        if isinstance(node.value, str):
            self._check_string_for_sql(node.value)
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _empty_result(filepath: str, error: str | None = None) -> dict[str, Any]:
    return {
        "filepath": filepath,
        "language": "python",
        "parse_error": error,
        "functions": [],
        "classes": [],
        "imports": [],
        "calls": [],
        "module_variables": [],
        "security_flags": {
            "uses_eval": False,
            "uses_exec": False,
            "uses_os_system": False,
            "uses_subprocess": False,
            "uses_pickle": False,
            "has_sql_string": False,
            "has_hardcoded_str": False,
        },
        "stats": {
            "total_functions": 0,
            "total_classes": 0,
            "total_imports": 0,
            "total_calls": 0,
            "lines_of_code": 0,
        },
    }


def parse_python_file(filepath: str, source: str) -> dict[str, Any]:
    """
    Parse a Python source string and return a structured dict representing
    the file's anatomy.

    Args:
        filepath: Relative path of the file (for reference only, not read from disk).
        source:   Raw UTF-8 source code string from file_reader.py output.

    Returns:
        A dict matching the documented output schema. Never raises.
    """
    lines_of_code = source.count("\n") + (1 if source and not source.endswith("\n") else 0)

    # --- Parse ---
    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError as exc:
        msg = f"SyntaxError in {filepath}: {exc}"
        logger.warning(msg)
        result = _empty_result(filepath, error=str(exc))
        result["stats"]["lines_of_code"] = lines_of_code
        return result
    except Exception as exc:
        msg = f"Unexpected error parsing {filepath}: {exc}"
        logger.error(msg)
        result = _empty_result(filepath, error=str(exc))
        result["stats"]["lines_of_code"] = lines_of_code
        return result

    # --- Visit ---
    try:
        visitor = _CodeVisitor()
        visitor.visit(tree)
    except Exception as exc:
        msg = f"Unexpected error visiting AST for {filepath}: {exc}"
        logger.error(msg)
        result = _empty_result(filepath, error=str(exc))
        result["stats"]["lines_of_code"] = lines_of_code
        return result

    return {
        "filepath": filepath,
        "language": "python",
        "parse_error": None,
        "functions": visitor.functions,
        "classes": visitor.classes,
        "imports": visitor.imports,
        "calls": visitor.calls,
        "module_variables": visitor.module_variables,
        "security_flags": {
            "uses_eval": visitor.uses_eval,
            "uses_exec": visitor.uses_exec,
            "uses_os_system": visitor.uses_os_system,
            "uses_subprocess": visitor.uses_subprocess,
            "uses_pickle": visitor.uses_pickle,
            "has_sql_string": visitor.has_sql_string,
            "has_hardcoded_str": visitor.has_hardcoded_str,
        },
        "stats": {
            "total_functions": len(visitor.functions),
            "total_classes": len(visitor.classes),
            "total_imports": len(visitor.imports),
            "total_calls": len(visitor.calls),
            "lines_of_code": lines_of_code,
        },
    }


# ---------------------------------------------------------------------------
# Quick smoke-test when run directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Only for direct script execution — never imported by the app
    import json
    import sys
    import logging as _logging

    _logging.basicConfig(level=_logging.DEBUG, format="%(levelname)s  %(name)s  %(message)s")

    _SAMPLE = """
import os
import subprocess
from flask import request

SECRET_KEY = "hunter2"
DB_URL: str = "SELECT * FROM users"

class UserAuth(object):
    def login(self, user, pwd):
        os.system(pwd)
        return eval(user)

    async def verify(self, token):
        return token

def standalone(x, y, z=1):
    cursor.execute("SELECT id FROM users WHERE name=?", (x,))
    return x + y
"""

    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as _f:
            _source = _f.read()
        _path = sys.argv[1]
    else:
        _source = _SAMPLE
        _path = "sample.py"

    result = parse_python_file(_path, _source)
    print(json.dumps(result, indent=2))
