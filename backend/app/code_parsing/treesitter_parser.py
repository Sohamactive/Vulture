"""
treesitter_parser.py
Parse non-Python source files with Tree-sitter and return the same schema
as ast_parser.py so all downstream modules need zero branching logic.
"""
from __future__ import annotations

from typing import Any

try:
    from app.logger import get_logger
except ImportError:
    import logging as _logging
    def get_logger(name: str) -> _logging.Logger:  # type: ignore[misc]
        return _logging.getLogger(name)

logger = get_logger(__name__)

_SQL_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE")

# ---------------------------------------------------------------------------
# Lazy grammar registry
# Each entry: extension → callable that returns a tree_sitter.Language object
# ---------------------------------------------------------------------------
def _grammar_loaders() -> dict[str, Any]:
    """Build extension → Language mapping at first call, skip missing grammars."""
    from tree_sitter import Language

    loaders: dict[str, Any] = {}

    def _try(ext: str, fn):
        try:
            loaders[ext] = Language(fn())
        except Exception:
            pass  # grammar not installed — will surface as parse_error at call time

    try:
        import tree_sitter_javascript as _tsj
        _try(".js",  _tsj.language)
        _try(".jsx", _tsj.language)
    except ImportError:
        pass

    try:
        import tree_sitter_typescript as _tst
        _try(".ts",  _tst.language_typescript)
        _try(".tsx", _tst.language_tsx)
    except ImportError:
        pass

    try:
        import tree_sitter_go as _tsg
        _try(".go", _tsg.language)
    except ImportError:
        pass

    try:
        import tree_sitter_java as _tsja
        _try(".java", _tsja.language)
    except ImportError:
        pass

    try:
        import tree_sitter_rust as _tsr
        _try(".rs", _tsr.language)
    except ImportError:
        pass

    try:
        import tree_sitter_ruby as _tsrb
        _try(".rb", _tsrb.language)
    except ImportError:
        pass

    try:
        import tree_sitter_php as _tsphp
        _try(".php", _tsphp.language_php)
    except ImportError:
        pass

    try:
        import tree_sitter_c as _tsc
        _try(".c", _tsc.language)
        _try(".h", _tsc.language)
    except ImportError:
        pass

    try:
        import tree_sitter_cpp as _tscpp
        _try(".cpp", _tscpp.language)
    except ImportError:
        pass

    return loaders


# Loaded once on first call to parse_file
_GRAMMARS: dict[str, Any] | None = None

def _get_grammars() -> dict[str, Any]:
    global _GRAMMARS
    if _GRAMMARS is None:
        _GRAMMARS = _grammar_loaders()
    return _GRAMMARS


# Extension → human-readable language name
_EXT_TO_LANG = {
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go", ".java": "java", ".rs": "rust",
    ".rb": "ruby", ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp",
}

# ---------------------------------------------------------------------------
# Node-type sets per language family
# ---------------------------------------------------------------------------
_FUNCTION_TYPES = {
    "function_declaration", "function_definition", "function_expression",
    "arrow_function", "method_definition", "method_declaration",
    "method", "singleton_method",
    "function_item",           # Rust
    "constructor_declaration", # Java
}

_CLASS_TYPES = {
    "class_declaration", "class_expression",
    "interface_declaration",   # Java/TS
    "impl_item", "struct_item",# Rust
    "type_declaration",        # Go structs
    "module",                  # Ruby
}

_IMPORT_TYPES = {
    "import_statement", "import_declaration",
    "use_declaration",         # Rust
    "preproc_include",         # C/C++
}

_CALL_TYPES = {"call_expression", "new_expression"}

_VARIABLE_TYPES = {
    "lexical_declaration", "variable_declaration",
    "var_declaration", "const_declaration",
    "field_declaration",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _child_text(node, field: str, source_bytes: bytes) -> str:
    """Return text of the first child with the given field name, or ''."""
    child = node.child_by_field_name(field)
    if child:
        return _get_node_text(child, source_bytes)
    return ""


def _first_named_child_text(node, type_name: str, source_bytes: bytes) -> str:
    for c in node.named_children:
        if c.type == type_name:
            return _get_node_text(c, source_bytes)
    return ""


def _resolve_callee(node, source_bytes: bytes) -> str:
    """
    Resolve a call_expression's function/callee to a dotted string.
    Handles: identifier, member_expression, qualified_name, selector_expr (Go).
    """
    # JS/TS/Java/Rust: 'function' field
    fn_node = node.child_by_field_name("function")
    if fn_node is None:
        # Try first named child
        fn_node = node.named_children[0] if node.named_children else None
    if fn_node is None:
        return "<unknown>"
    t = fn_node.type
    if t in ("identifier", "simple_identifier", "name"):
        return _get_node_text(fn_node, source_bytes)
    if t in ("member_expression", "field_access", "selector_expr",
             "qualified_identifier", "scoped_identifier", "attribute"):
        return _get_node_text(fn_node, source_bytes).replace("\n", ".")
    return _get_node_text(fn_node, source_bytes)


def _count_args(node) -> int:
    """Count arguments inside a call_expression."""
    for field in ("arguments", "argument_list"):
        args_node = node.child_by_field_name(field)
        if args_node:
            return sum(1 for c in args_node.named_children
                       if c.type not in ("comment",))
    return 0


def _is_async(node) -> bool:
    for c in node.children:
        if c.type == "async":
            return True
    return False


def _extract_params(node, source_bytes: bytes) -> list[str]:
    """Pull parameter/identifier names from a parameters child."""
    params: list[str] = []
    for field in ("parameters", "formal_parameters", "parameter_list", "arguments"):
        pnode = node.child_by_field_name(field)
        if pnode:
            for c in pnode.named_children:
                if c.type in ("identifier", "simple_identifier", "required_parameter",
                              "optional_parameter", "rest_pattern", "pair_pattern"):
                    # For typed params, grab the identifier inside
                    ident = c.child_by_field_name("pattern") or \
                            c.child_by_field_name("name") or \
                            (c if c.type in ("identifier", "simple_identifier") else None)
                    if ident:
                        params.append(_get_node_text(ident, source_bytes))
            break
    return params


def _extract_decorators(node, source_bytes: bytes) -> list[str]:
    decorators = []
    # Look for preceding decorator siblings
    sib = node.prev_named_sibling
    while sib and sib.type in ("decorator", "attribute_item"):
        decorators.insert(0, _get_node_text(sib, source_bytes).lstrip("@").split("(")[0].strip())
        sib = sib.prev_named_sibling
    return decorators


def _string_has_sql(text: str) -> bool:
    upper = text.upper()
    return any(kw in upper for kw in _SQL_KEYWORDS)


def _callee_flags(callee: str) -> dict[str, bool]:
    """Return security flag updates triggered by a callee name."""
    low = callee.lower()
    return {
        "uses_eval": "eval" in low,
        "uses_exec": any(x in low for x in ("exec", "execsync")),
        "uses_os_system": "system" in low,
        "uses_subprocess": any(x in low for x in
                               ("spawn", "fork", "execfile", "child_process", "subprocess")),
    }


# ---------------------------------------------------------------------------
# Empty result (identical structure to ast_parser._empty_result)
# ---------------------------------------------------------------------------

def _empty_result(filepath: str, language: str, error: str | None = None) -> dict[str, Any]:
    return {
        "filepath": filepath,
        "language": language,
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


# ---------------------------------------------------------------------------
# Tree walker
# ---------------------------------------------------------------------------

class _Extractor:
    """
    Recursive tree walker with a scope_stack identical in concept to
    ast_parser._CodeVisitor._scope_stack.
    """

    def __init__(self, source_bytes: bytes) -> None:
        self.src = source_bytes
        self.scope_stack: list[str] = ["module_level"]

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

    @property
    def _scope(self) -> str:
        return self.scope_stack[-1]

    def _txt(self, node) -> str:
        return _get_node_text(node, self.src)

    def walk(self, node) -> None:
        t = node.type

        if t in _FUNCTION_TYPES:
            self._handle_function(node)
            return  # _handle_function recurses inside the body

        if t in _CLASS_TYPES:
            self._handle_class(node)
            return  # _handle_class already recurses children — don't double-walk

        if t in _IMPORT_TYPES:
            self._handle_import(node)
            # no return — let children recurse for nested nodes

        if t in _CALL_TYPES:
            self._handle_call(node)
            # still recurse children for nested calls

        if t in _VARIABLE_TYPES and self._scope == "module_level":
            self._handle_variable(node)

        if t == "string":
            text = self._txt(node).strip("'\"` \t")
            if _string_has_sql(text):
                self.has_sql_string = True

        for child in node.children:
            self.walk(child)

    def _handle_function(self, node) -> None:
        # --- name ---
        name = (
            _child_text(node, "name", self.src)
            or _first_named_child_text(node, "identifier", self.src)
            or _first_named_child_text(node, "property_identifier", self.src)
            or "<anonymous>"
        )

        # --- calls_made (deduplicated list for the functions[] bucket) ---
        calls_made = self._collect_calls_made(node)

        self.functions.append({
            "name": name,
            "line_start": node.start_point[0] + 1,
            "line_end": node.end_point[0] + 1,
            "args": _extract_params(node, self.src),
            "is_async": _is_async(node),
            "decorators": _extract_decorators(node, self.src),
            "calls_made": calls_made,
        })

        self.scope_stack.append(name)
        for child in node.children:
            self.walk(child)
        self.scope_stack.pop()

    def _collect_calls_made(self, node) -> list[str]:
        """Deduplicated call names inside a function subtree (for functions[].calls_made)."""
        seen: set[str] = set()
        result: list[str] = []

        def _recurse(n):
            if n.type in _CALL_TYPES:
                callee = _resolve_callee(n, self.src)
                if callee not in seen:
                    seen.add(callee)
                    result.append(callee)
            for c in n.children:
                _recurse(c)

        _recurse(node)
        return result

    def _handle_class(self, node) -> None:
        name = (
            _child_text(node, "name", self.src)
            or _first_named_child_text(node, "identifier", self.src)
            or "<anonymous>"
        )

        # base classes / superclass
        base_classes: list[str] = []
        heritage = node.child_by_field_name("superclass")
        if heritage:
            base_classes.append(self._txt(heritage))
        # Java/TS implements
        for c in node.named_children:
            if c.type in ("class_heritage", "superclasses", "interfaces"):
                for ident in c.named_children:
                    if ident.type in ("identifier", "type_identifier"):
                        base_classes.append(self._txt(ident))

        # direct methods (one level deep)
        methods: list[str] = []
        body = node.child_by_field_name("body")
        if body:
            for c in body.named_children:
                if c.type in _FUNCTION_TYPES:
                    m_name = (
                        _child_text(c, "name", self.src)
                        or _first_named_child_text(c, "property_identifier", self.src)
                        or _first_named_child_text(c, "identifier", self.src)
                    )
                    if m_name:
                        methods.append(m_name)

        self.classes.append({
            "name": name,
            "line_start": node.start_point[0] + 1,
            "line_end": node.end_point[0] + 1,
            "base_classes": base_classes,
            "methods": methods,
        })

        # recurse into body so methods/calls inside classes are captured
        for child in node.children:
            self.walk(child)
        # NOTE: walk() returns after calling _handle_class, so children are
        # only visited once — from here, not from the bottom of walk().

    def _handle_import(self, node) -> None:
        t = node.type
        module = ""
        names: list[str] = []
        aliases: list[str] = []
        is_from = False

        if t == "import_statement":
            # JS/TS: import { a, b } from 'mod'  /  import mod from 'mod'
            src_node = node.child_by_field_name("source")
            if src_node:
                module = self._txt(src_node).strip("'\"` ")
            clause = node.child_by_field_name("import")
            if clause is None:
                for c in node.named_children:
                    if c.type == "named_imports":
                        clause = c
                        break
            if clause:
                is_from = True
                for spec in clause.named_children:
                    if spec.type == "import_specifier":
                        n_node = spec.child_by_field_name("name")
                        a_node = spec.child_by_field_name("alias")
                        if n_node:
                            names.append(self._txt(n_node))
                        if a_node:
                            aliases.append(self._txt(a_node))

        elif t == "import_declaration":
            # Go: import ( "fmt" \n "os" )
            # Structure: import_declaration → import_spec_list → import_spec
            spec_list = next(
                (c for c in node.named_children if c.type == "import_spec_list"),
                node,  # fallback: single-import form has import_spec directly
            )
            for spec in spec_list.named_children:
                if spec.type != "import_spec":
                    continue
                path_node = spec.child_by_field_name("path")
                if path_node is None:
                    continue
                # Prefer the inner content node (no quotes); fall back to strip
                content = next(
                    (c for c in path_node.named_children
                     if "content" in c.type or c.type == "interpreted_string_literal_content"),
                    None,
                )
                mod = self._txt(content) if content else self._txt(path_node).strip('"\'')
                self.imports.append({
                    "module": mod,
                    "names": [],
                    "alias": [],
                    "line": spec.start_point[0] + 1,
                    "is_from_import": False,
                })
                if mod in ("subprocess", "child_process"):
                    self.uses_subprocess = True
            return  # already appended — skip the generic append below


        elif t == "use_declaration":
            # Rust: use std::io::{Read, Write};
            module = self._txt(node).removeprefix("use ").rstrip(";").strip()
            is_from = True

        elif t == "preproc_include":
            # C/C++: #include <stdio.h> or "header.h"
            path = node.child_by_field_name("path")
            if path:
                module = self._txt(path).strip("<>\"")

        self.imports.append({
            "module": module,
            "names": names,
            "alias": aliases,
            "line": node.start_point[0] + 1,
            "is_from_import": is_from,
        })

        # Check for pickle/subprocess imports
        mod_root = module.split(".")[0].split("/")[-1].split("\\")[-1]
        if mod_root in ("pickle", "marshal"):
            self.uses_pickle = True
        if mod_root in ("subprocess", "child_process"):
            self.uses_subprocess = True

    def _handle_call(self, node) -> None:
        callee = _resolve_callee(node, self.src)
        self.calls.append({
            "caller_function": self._scope,
            "callee": callee,
            "line": node.start_point[0] + 1,
            "args_count": _count_args(node),
        })

        flags = _callee_flags(callee)
        if flags["uses_eval"]:
            self.uses_eval = True
        if flags["uses_exec"]:
            self.uses_exec = True
        if flags["uses_os_system"]:
            self.uses_os_system = True
        if flags["uses_subprocess"]:
            self.uses_subprocess = True

    def _handle_variable(self, node) -> None:
        """Capture top-level variable declarations."""
        for c in node.named_children:
            if c.type in ("variable_declarator", "const_spec", "var_spec"):
                name_node = c.child_by_field_name("name")
                val_node = c.child_by_field_name("value")
                if name_node is None:
                    name_node = c.named_children[0] if c.named_children else None
                if name_node:
                    is_str = val_node is not None and val_node.type in (
                        "string", "interpreted_string_literal",
                        "raw_string_literal", "template_string",
                    )
                    if is_str:
                        self.has_hardcoded_str = True
                    self.module_variables.append({
                        "name": self._txt(name_node),
                        "line": c.start_point[0] + 1,
                        "has_string_value": is_str,
                    })


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_file(filepath: str, source: str) -> dict[str, Any]:
    """
    Parse a non-Python source file and return a structured dict with the
    same schema as ast_parser.parse_python_file(). Never raises.

    Args:
        filepath: Relative path (used for extension detection and display).
        source:   Raw UTF-8 source code string from file_reader.py.
    """
    import os
    ext = os.path.splitext(filepath)[1].lower()
    language = _EXT_TO_LANG.get(ext, ext.lstrip(".") or "unknown")
    lines_of_code = sum(1 for ln in source.splitlines() if ln.strip())

    # --- Extension supported? ---
    grammars = _get_grammars()
    if ext not in grammars:
        msg = f"unsupported language: {ext!r}"
        logger.warning(f"{filepath}: {msg}")
        result = _empty_result(filepath, language, error=msg)
        result["stats"]["lines_of_code"] = lines_of_code
        return result

    # --- Parse ---
    try:
        from tree_sitter import Parser
        parser = Parser(grammars[ext])
        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
    except Exception as exc:
        msg = f"parse failed: {exc}"
        logger.error(f"{filepath}: {msg}")
        result = _empty_result(filepath, language, error=msg)
        result["stats"]["lines_of_code"] = lines_of_code
        return result

    parse_error = None
    if tree.root_node.has_error:
        parse_error = "partial parse — syntax errors detected"
        logger.warning(f"{filepath}: {parse_error}")

    # --- Walk ---
    try:
        extractor = _Extractor(source_bytes)
        extractor.walk(tree.root_node)
    except Exception as exc:
        msg = f"extraction failed: {exc}"
        logger.error(f"{filepath}: {msg}")
        result = _empty_result(filepath, language, error=msg)
        result["stats"]["lines_of_code"] = lines_of_code
        return result

    return {
        "filepath": filepath,
        "language": language,
        "parse_error": parse_error,
        "functions": extractor.functions,
        "classes": extractor.classes,
        "imports": extractor.imports,
        "calls": extractor.calls,
        "module_variables": extractor.module_variables,
        "security_flags": {
            "uses_eval": extractor.uses_eval,
            "uses_exec": extractor.uses_exec,
            "uses_os_system": extractor.uses_os_system,
            "uses_subprocess": extractor.uses_subprocess,
            "uses_pickle": extractor.uses_pickle,
            "has_sql_string": extractor.has_sql_string,
            "has_hardcoded_str": extractor.has_hardcoded_str,
        },
        "stats": {
            "total_functions": len(extractor.functions),
            "total_classes": len(extractor.classes),
            "total_imports": len(extractor.imports),
            "total_calls": len(extractor.calls),
            "lines_of_code": lines_of_code,
        },
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Only for direct script execution — never imported by the app
    import json, sys
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(levelname)s  %(name)s  %(message)s")

    _JS_SAMPLE = """\
import { readFile } from 'fs';
import child_process from 'child_process';

const SECRET = 'hunter2';
const QUERY = 'SELECT * FROM users WHERE id = ?';

async function fetchUser(id, name) {
  eval(id);
  return db.query('SELECT * FROM sessions');
}

class AuthService extends BaseService {
  constructor(cfg) {
    super(cfg);
  }
  async login(user, pwd) {
    child_process.exec(pwd);
    return this.verify(user);
  }
}
"""
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as _f:
            _src = _f.read()
        _path = sys.argv[1]
    else:
        _src = _JS_SAMPLE
        _path = "sample.js"

    result = parse_file(_path, _src)
    print(json.dumps(result, indent=2))
