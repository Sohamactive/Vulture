"""
call_graph.py
Consume a list of per-file parse results (from ast_parser /
treesitter_parser) and build a cross-file call graph + dependency
graph that the LLM agent can query to understand how the codebase
is wired together.

Constraints:
  - Pure Python — no subprocess, no shell, no file writes
  - Only reads from the parse_results list passed in as argument
  - Never imports or modifies any other module in backend/app/
    except app.logger
  - Never raises — always returns the output dict
  - No LLM calls
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from app.logger import get_logger
except ImportError:
    import logging as _logging

    def get_logger(name: str) -> _logging.Logger:  # type: ignore[misc]
        return _logging.getLogger(name)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_module_to_file(module: str, known_files: list[str]) -> str | None:
    """Try to map a dotted module name to a filepath in known_files."""
    parts = module.replace("-", "_").split(".")
    suffix_py   = "/".join(parts) + ".py"
    suffix_init = "/".join(parts) + "/__init__.py"
    for f in known_files:
        normalized = f.replace("\\", "/")
        if normalized.endswith(suffix_py) or normalized.endswith(suffix_init):
            return f
    return None


def _find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """DFS cycle detection on the import graph. Returns list of cycle paths."""
    visited: set[str] = set()
    rec_stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        visited.add(node)
        rec_stack.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                idx = rec_stack.index(neighbor)
                cycles.append(rec_stack[idx:] + [neighbor])
        rec_stack.pop()

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)

    return cycles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_call_graph(parse_results: list[dict]) -> dict:  # noqa: C901
    """
    Build a cross-file call graph and dependency graph from a list of
    per-file parse results.

    Args:
        parse_results: List of dicts from ast_parser.parse_python_file()
                       or treesitter_parser.parse_file(). Schema is
                       identical between both parsers.

    Returns:
        A structured dict with symbol_table, import_graph, call_edges,
        circular_imports, file_metrics, hotspots, unresolved_calls, and
        stats. Never raises.
    """
    try:
        return _build(parse_results)
    except Exception as exc:
        logger.error(f"build_call_graph: unexpected error: {exc}", exc_info=True)
        return _empty_result(str(exc))


def _empty_result(error: str = "") -> dict:
    return {
        "symbol_table": {},
        "symbol_definitions": {},
        "import_graph": {},
        "external_imports": {},
        "call_edges": [],
        "circular_imports": [],
        "file_metrics": {},
        "hotspots": [],
        "unresolved_calls": [],
        "stats": {
            "total_files": 0,
            "total_symbols": 0,
            "duplicate_symbols": 0,
            "total_call_edges": 0,
            "resolved_call_edges": 0,
            "unresolved_call_edges": 0,
            "resolution_rate": 0.0,
            "circular_import_count": 0,
            "files_with_errors": 0,
            "build_error": error,
        },
    }


def _build(parse_results: list[dict]) -> dict:  # noqa: C901
    known_files: list[str] = [pr.get("filepath", "") for pr in parse_results]

    # -----------------------------------------------------------------------
    # STEP 1 — Build symbol table
    # -----------------------------------------------------------------------
    # symbol_definitions: symbol → [filepath, ...]   (all definitions)
    symbol_definitions: dict[str, list[str]] = defaultdict(list)

    for pr in parse_results:
        fp = pr.get("filepath", "")

        for fn in pr.get("functions", []):
            name = fn.get("name", "")
            if name:
                symbol_definitions[name].append(fp)

        for cls in pr.get("classes", []):
            cls_name = cls.get("name", "")
            if cls_name:
                symbol_definitions[cls_name].append(fp)
            for method in cls.get("methods", []):
                if method:
                    key = f"{cls_name}.{method}"
                    symbol_definitions[key].append(fp)

    # symbol_table: quick lookup → first definition
    symbol_table: dict[str, str] = {
        sym: defs[0] for sym, defs in symbol_definitions.items() if defs
    }

    logger.debug(
        f"Symbol table built: {len(symbol_table)} symbols, "
        f"{sum(1 for d in symbol_definitions.values() if len(d) > 1)} duplicates"
    )

    # -----------------------------------------------------------------------
    # STEP 2 — Build file-level import graph
    # -----------------------------------------------------------------------
    import_graph: dict[str, list[str]] = defaultdict(list)
    external_imports: dict[str, list[str]] = defaultdict(list)

    for pr in parse_results:
        fp = pr.get("filepath", "")
        for imp in pr.get("imports", []):
            module = imp.get("module", "")
            if not module:
                continue
            resolved = _resolve_module_to_file(module, known_files)
            if resolved and resolved != fp:
                if resolved not in import_graph[fp]:
                    import_graph[fp].append(resolved)
            else:
                if module not in external_imports[fp]:
                    external_imports[fp].append(module)

    # Ensure every file has an entry even if it has no imports
    for fp in known_files:
        if fp not in import_graph:
            import_graph[fp] = []

    # -----------------------------------------------------------------------
    # STEP 3 — Build function-level call graph
    # -----------------------------------------------------------------------
    call_edges: list[dict] = []

    for pr in parse_results:
        fp = pr.get("filepath", "")
        for call in pr.get("calls", []):
            callee_raw = call.get("callee", "")
            caller_fn  = call.get("caller_function", "<module>")
            line       = call.get("line", 0)

            callee_file:     str | None = None
            callee_resolved: bool       = False

            # Direct name match
            if callee_raw in symbol_table:
                callee_file     = symbol_table[callee_raw]
                callee_resolved = True

            # Dotted call: obj.method / Class.method / a.b.c
            elif "." in callee_raw:
                parts = callee_raw.split(".")
                # Try last segment only (method name)
                if parts[-1] in symbol_table:
                    callee_file     = symbol_table[parts[-1]]
                    callee_resolved = True
                # Try Class.method (second-to-last . last)
                if len(parts) >= 2:
                    dot_key = f"{parts[-2]}.{parts[-1]}"
                    if dot_key in symbol_table:
                        callee_file     = symbol_table[dot_key]
                        callee_resolved = True

            call_edges.append(
                {
                    "caller_file":     fp,
                    "caller_function": caller_fn,
                    "callee":          callee_raw,
                    "callee_file":     callee_file,
                    "callee_resolved": callee_resolved,
                    "line":            line,
                }
            )

    # -----------------------------------------------------------------------
    # STEP 4 — Detect circular imports
    # -----------------------------------------------------------------------
    circular_imports = _find_cycles(dict(import_graph))

    # -----------------------------------------------------------------------
    # STEP 5 — Compute per-file metrics
    # -----------------------------------------------------------------------
    # in_degree: count how many other files list this file as an import target
    in_degree_counter: dict[str, int] = defaultdict(int)
    for targets in import_graph.values():
        for t in targets:
            in_degree_counter[t] += 1

    # call in/out counts
    call_out_counter: dict[str, int] = defaultdict(int)
    call_in_counter:  dict[str, int] = defaultdict(int)
    for edge in call_edges:
        call_out_counter[edge["caller_file"]] += 1
        if edge["callee_file"]:
            call_in_counter[edge["callee_file"]] += 1

    file_metrics: dict[str, dict] = {}
    for fp in known_files:
        in_deg  = in_degree_counter.get(fp, 0)
        out_deg = len(import_graph.get(fp, []))
        file_metrics[fp] = {
            "in_degree":      in_deg,
            "out_degree":     out_deg,
            "call_out_count": call_out_counter.get(fp, 0),
            "call_in_count":  call_in_counter.get(fp, 0),
            "is_entry_point": in_deg == 0 and out_deg > 0,
            "is_utility":     in_deg > 2 and out_deg <= 1,
            "is_isolated":    in_deg == 0 and out_deg == 0,
        }

    # -----------------------------------------------------------------------
    # STEP 6 — Find hotspots (top 5 by in_degree, excluding 0)
    # -----------------------------------------------------------------------
    # Build reverse map: filepath → symbols defined there
    symbols_by_file: dict[str, list[str]] = defaultdict(list)
    for sym, fp in symbol_table.items():
        symbols_by_file[fp].append(sym)

    sorted_by_in = sorted(
        [(fp, file_metrics[fp]["in_degree"]) for fp in known_files],
        key=lambda x: x[1],
        reverse=True,
    )
    hotspots: list[dict] = []
    for fp, in_deg in sorted_by_in:
        if in_deg == 0:
            break
        hotspots.append(
            {
                "filepath":        fp,
                "in_degree":       in_deg,
                "defined_symbols": sorted(symbols_by_file.get(fp, [])),
            }
        )
        if len(hotspots) >= 5:
            break

    # -----------------------------------------------------------------------
    # STEP 7 — Unresolved calls summary
    # -----------------------------------------------------------------------
    unresolved_counter: dict[str, dict] = {}
    for edge in call_edges:
        if edge["callee_resolved"]:
            continue
        callee = edge["callee"]
        if callee not in unresolved_counter:
            unresolved_counter[callee] = {
                "callee":       callee,
                "call_count":   0,
                "example_file": edge["caller_file"],
            }
        unresolved_counter[callee]["call_count"] += 1

    unresolved_calls = sorted(
        unresolved_counter.values(),
        key=lambda x: x["call_count"],
        reverse=True,
    )

    # -----------------------------------------------------------------------
    # STEP 8 — Stats
    # -----------------------------------------------------------------------
    total_edges    = len(call_edges)
    resolved_edges = sum(1 for e in call_edges if e["callee_resolved"])
    dup_symbols    = sum(1 for d in symbol_definitions.values() if len(d) > 1)
    files_with_err = sum(1 for pr in parse_results if pr.get("parse_error"))

    stats = {
        "total_files":           len(known_files),
        "total_symbols":         len(symbol_table),
        "duplicate_symbols":     dup_symbols,
        "total_call_edges":      total_edges,
        "resolved_call_edges":   resolved_edges,
        "unresolved_call_edges": total_edges - resolved_edges,
        "resolution_rate":       (resolved_edges / total_edges) if total_edges > 0 else 0.0,
        "circular_import_count": len(circular_imports),
        "files_with_errors":     files_with_err,
    }

    logger.info(
        f"call_graph built: {len(known_files)} files, "
        f"{len(symbol_table)} symbols, "
        f"{total_edges} call edges ({resolved_edges} resolved, "
        f"{stats['resolution_rate']:.1%} rate), "
        f"{len(circular_imports)} circular import(s)"
    )

    return {
        "symbol_table":       symbol_table,
        "symbol_definitions": {k: v for k, v in symbol_definitions.items()},
        "import_graph":       dict(import_graph),
        "external_imports":   dict(external_imports),
        "call_edges":         call_edges,
        "circular_imports":   circular_imports,
        "file_metrics":       file_metrics,
        "hotspots":           hotspots,
        "unresolved_calls":   list(unresolved_calls),
        "stats":              stats,
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import logging as _logging

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
    )

    # ── Fake parse results ─────────────────────────────────────────────────
    result_main = {
        "filepath":    "src/main.py",
        "language":    "python",
        "parse_error": None,
        "functions":   [{"name": "handle_login", "calls_made": ["AuthService.login"]}],
        "classes":     [],
        "imports":     [{"module": "src.auth", "names": ["AuthService"]},
                        {"module": "fastapi",  "names": ["FastAPI"]}],
        "calls":       [{"caller_function": "handle_login",
                         "callee":          "AuthService.login",
                         "line":            12}],
        "stats":       {},
    }

    result_auth = {
        "filepath":    "src/auth.py",
        "language":    "python",
        "parse_error": None,
        "functions":   [{"name": "verify_token", "calls_made": ["fetch_user"]}],
        "classes":     [{"name": "AuthService",
                         "methods": ["login", "logout"]}],
        "imports":     [{"module": "src.users", "names": ["fetch_user"]},
                        {"module": "pydantic",  "names": ["BaseModel"]}],
        "calls":       [{"caller_function": "AuthService.login",
                         "callee":          "fetch_user",
                         "line":            31},
                        {"caller_function": "verify_token",
                         "callee":          "os.path.join",
                         "line":            55}],
        "stats":       {},
    }

    result_users = {
        "filepath":    "src/users.py",
        "language":    "python",
        "parse_error": None,
        "functions":   [{"name": "fetch_user", "calls_made": []}],
        "classes":     [],
        "imports":     [{"module": "sqlalchemy", "names": ["Session"]}],
        "calls":       [],
        "stats":       {},
    }

    graph = build_call_graph([result_main, result_auth, result_users])
    print(json.dumps(graph, indent=2))

    # ── Assertions ─────────────────────────────────────────────────────────
    failures = []

    if "fetch_user" not in graph["symbol_table"]:
        failures.append("FAIL: fetch_user not in symbol_table")
    if "AuthService" not in graph["symbol_table"]:
        failures.append("FAIL: AuthService not in symbol_table")
    if "AuthService.login" not in graph["symbol_table"]:
        failures.append("FAIL: AuthService.login not in symbol_table")

    if "src/auth.py" not in graph["import_graph"].get("src/main.py", []):
        failures.append("FAIL: import_graph['src/main.py'] does not contain src/auth.py")

    if not any(e["callee_resolved"] for e in graph["call_edges"]):
        failures.append("FAIL: no resolved call edges found")

    if graph["circular_imports"]:
        failures.append(f"FAIL: unexpected circular imports: {graph['circular_imports']}")

    if graph["stats"]["resolution_rate"] <= 0.0:
        failures.append("FAIL: resolution_rate should be > 0.0")

    if failures:
        for f in failures:
            print(f)
    else:
        print("\nAll assertions passed [OK]")
