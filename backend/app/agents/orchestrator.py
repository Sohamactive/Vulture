"""
orchestrator.py
Wire all code_parsing modules into a LangGraph StateGraph DAG.
Manages scan state, fans out to parsers in parallel, aggregates
results, and hands structured context to the LLM agent node.
Streams progress events back to the API layer via an async generator.

Constraints:
  - Orchestrates only — never reimplements parser logic
  - Never modifies any file in backend/app/code_parsing/
  - Never raises to the caller — yields error events instead
  - Stateless per invocation — no persistent storage
"""
from __future__ import annotations

import json
import os
import uuid
import re
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.agents.vuln_agent import run_vuln_agent

try:
    from app.code_parsing.ast_parser import parse_python_file
    from app.code_parsing.call_graph import build_call_graph
    from app.code_parsing.file_reader import read_codebase
    from app.code_parsing.semgrep_runner import run_semgrep
    from app.code_parsing.treesitter_parser import parse_file as parse_ts_file
    from app.logger import get_logger
except ImportError:
    import logging as _logging

    def get_logger(name: str) -> _logging.Logger:  # type: ignore[misc]
        return _logging.getLogger(name)

    # Allow running as __main__ without installed package
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from app.code_parsing.ast_parser import parse_python_file           # noqa: F811
    from app.code_parsing.call_graph import build_call_graph             # noqa: F811
    from app.code_parsing.file_reader import read_codebase               # noqa: F811
    from app.code_parsing.semgrep_runner import run_semgrep              # noqa: F811
    from app.code_parsing.treesitter_parser import parse_file as parse_ts_file  # noqa: F811

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TREESITTER_EXTENSIONS: frozenset[str] = frozenset({
    ".js", ".jsx", ".ts", ".tsx",
    ".go", ".java", ".rs", ".rb", ".php",
    ".c", ".cpp", ".h",
})

ALLOWED_OWASP_CATEGORIES: dict[str, str] = {
    "A01": "A01:Access Control",
    "A02": "A02:Crypto",
    "A03": "A03:Injection",
    "A04": "A04:Design",
    "A05": "A05:Config",
    "A06": "A06:Outdated",
    "A07": "A07:Auth",
    "A08": "A08:Integrity",
    "A09": "A09:Logging",
    "A10": "A10:SSRF",
}

# ---------------------------------------------------------------------------
# ScanState
# ---------------------------------------------------------------------------

class ScanState(TypedDict):
    # ── Input ────────────────────────────────────────────────────────────────
    repo_path:       str
    rules:           str

    # ── Stage outputs ────────────────────────────────────────────────────────
    file_reader_out: dict
    parse_results:   list[dict]
    semgrep_out:     dict
    call_graph_out:  dict
    agent_out:       dict
    final_report:    dict

    # ── Progress ─────────────────────────────────────────────────────────────
    # The two parallel branches write to their *own* key so LangGraph never
    # sees a concurrent write to the same field.  node_build_call_graph merges
    # them into `progress` at the fan-in point.
    parse_progress:  list[dict]   # written only by node_parse_files
    semgrep_progress: list[dict]  # written only by node_run_semgrep
    progress:        list[dict]   # accumulated by all other nodes
    current_stage:   str
    scan_error:      str | None
    scan_started_at: float

# ---------------------------------------------------------------------------
# Progress helper
# ---------------------------------------------------------------------------

def _event(stage: str, message: str, data: dict | None = None) -> dict:
    return {
        "stage":     stage,
        "message":   message,
        "data":      data or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if match:
            return int(match.group(0))
    return None


def _canonical_owasp(value: Any) -> str | None:
    if value is None:
        return None

    candidates: list[str] = []
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, list):
        candidates = [str(v) for v in value if v is not None]
    else:
        candidates = [str(value)]

    for raw in candidates:
        match = re.search(r"\bA(0[1-9]|10)\b", raw, flags=re.IGNORECASE)
        if not match:
            continue
        key = f"A{match.group(1)}".upper()
        mapped = ALLOWED_OWASP_CATEGORIES.get(key)
        if mapped:
            return mapped

    return None


def _normalize_cwe(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        for item in value:
            normalized = _normalize_cwe(item)
            if normalized:
                return normalized
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"(CWE-\d+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).upper()
    if text.isdigit():
        return f"CWE-{text}"
    return text


def _infer_owasp_from_text(text: str) -> str | None:
    lowered = text.lower()
    keyword_map = [
        ("A03", ("sql injection", "command injection", "xss", "injection")),
        ("A10", ("ssrf", "server-side request forgery")),
        ("A01", ("authorization", "access control", "privilege escalation", "idor")),
        ("A07", ("authentication", "auth bypass", "session fixation", "token")),
        ("A02", ("crypto", "encryption", "hardcoded key", "tls")),
        ("A05", ("cors", "misconfiguration", "exposed config", "security headers")),
        ("A06", ("outdated", "vulnerable dependency", "legacy package")),
        ("A08", ("integrity", "deserialization", "supply chain", "tamper")),
        ("A09", ("logging", "monitoring", "audit trail")),
        ("A04", ("insecure design", "design flaw", "business logic")),
    ]
    for key, terms in keyword_map:
        if any(term in lowered for term in terms):
            return ALLOWED_OWASP_CATEGORIES[key]
    return None


def _match_semgrep_finding(
    finding: dict[str, Any],
    semgrep_findings: list[dict[str, Any]],
) -> dict[str, Any] | None:
    line_start = _coerce_int(finding.get("line_start") or finding.get("line"))
    code_snippet = str(finding.get("code_snippet") or "").strip()
    title = str(finding.get("title") or "").lower()
    description = str(finding.get("description") or "").lower()

    candidates: list[dict[str, Any]] = []

    if line_start is not None:
        line_candidates = [
            sf for sf in semgrep_findings
            if _coerce_int(sf.get("line_start")) == line_start
        ]
        if len(line_candidates) == 1:
            return line_candidates[0]
        candidates.extend(line_candidates)

    if code_snippet:
        snippet_candidates = [
            sf for sf in semgrep_findings
            if code_snippet in str(sf.get("code_snippet", ""))
            or str(sf.get("code_snippet", "")) in code_snippet
        ]
        if len(snippet_candidates) == 1:
            return snippet_candidates[0]
        candidates.extend(snippet_candidates)

    if title or description:
        text = f"{title} {description}"
        text_candidates = [
            sf for sf in semgrep_findings
            if str(sf.get("rule_name", "")).lower() in text
            or str(sf.get("rule_id", "")).lower() in text
            or str(sf.get("message", "")).lower() in text
        ]
        if len(text_candidates) == 1:
            return text_candidates[0]
        candidates.extend(text_candidates)

    if len(candidates) == 1:
        return candidates[0]
    return None


def _normalize_agent_output(agent_out: dict[str, Any], state: ScanState) -> dict[str, Any]:
    semgrep_findings: list[dict[str, Any]] = state.get("semgrep_out", {}).get("findings", [])
    raw_findings = agent_out.get("findings", [])
    if not isinstance(raw_findings, list):
        agent_out["findings"] = []
        return agent_out

    normalized_findings: list[dict[str, Any]] = []
    seen: set[tuple[Any, Any, Any]] = set()

    for finding in raw_findings:
        if not isinstance(finding, dict):
            continue

        filepath = (
            finding.get("filepath")
            or finding.get("file_path")
            or finding.get("file")
            or finding.get("path")
        )
        line_start = _coerce_int(finding.get("line_start") or finding.get("line"))
        line_end = _coerce_int(finding.get("line_end"))

        semgrep_match = _match_semgrep_finding(finding, semgrep_findings)
        if not filepath and semgrep_match:
            filepath = semgrep_match.get("filepath")

        owasp_category = _canonical_owasp(
            finding.get("owasp_category") or finding.get("owasp")
        )
        if not owasp_category and semgrep_match:
            owasp_category = _canonical_owasp(semgrep_match.get("owasp"))
        if not owasp_category:
            owasp_category = _infer_owasp_from_text(
                f"{finding.get('title', '')} {finding.get('description', '')}"
            )

        cwe_value = _normalize_cwe(finding.get("cwe_id") or finding.get("cwe"))
        if not cwe_value and semgrep_match:
            cwe_value = _normalize_cwe(semgrep_match.get("cwe"))

        severity = str(finding.get("severity", "MEDIUM")).upper()
        if severity in {"ERROR", "CRITICAL"}:
            severity = "CRITICAL"
        elif severity in {"WARNING", "WARN", "HIGH"}:
            severity = "HIGH"
        elif severity in {"INFO", "LOW"}:
            severity = "LOW"
        elif severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            severity = "MEDIUM"

        normalized = dict(finding)
        normalized["filepath"] = filepath
        normalized["file_path"] = filepath
        normalized["line_start"] = line_start
        normalized["line_end"] = line_end
        normalized["owasp_category"] = owasp_category
        normalized["cwe"] = cwe_value
        normalized["cwe_id"] = cwe_value
        normalized["severity"] = severity

        dedupe_key = (
            normalized.get("filepath"),
            normalized.get("line_start"),
            str(normalized.get("title", "")).strip().lower(),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        normalized_findings.append(normalized)

    agent_out["findings"] = normalized_findings
    return agent_out


# ---------------------------------------------------------------------------
# NODE 1 — Read files
# ---------------------------------------------------------------------------

def node_read_files(state: ScanState) -> dict:
    repo_path = state["repo_path"]
    logger.info(f"[node_read_files] repo_path={repo_path}")

    try:
        result = read_codebase(repo_path)
    except Exception as exc:
        logger.error(f"[node_read_files] failed: {exc}")
        return {
            "file_reader_out": {},
            "progress":        [_event("file_reader", "Reading codebase...", {"path": repo_path}),
                                _event("file_reader", f"Failed to read codebase: {exc}")],
            "scan_error":      str(exc),
            "current_stage":   "file_reader_error",
        }

    meta = result.get("metadata", {})
    return {
        "file_reader_out": result,
        "progress":        [
            _event("file_reader", "Reading codebase...", {"path": repo_path}),
            _event(
                "file_reader",
                f"Found {meta.get('total_files', 0)} files",
                {
                    "total_files": meta.get("total_files", 0),
                    "languages":   meta.get("languages_detected", []),
                },
            ),
        ],
        "current_stage":   "file_reader_done",
        "scan_error":      None,
    }

# ---------------------------------------------------------------------------
# NODE 2 — Parse files (AST + Tree-sitter)
# ---------------------------------------------------------------------------

def node_parse_files(state: ScanState) -> dict:
    logger.info("[node_parse_files] starting")

    if state.get("scan_error"):
        # Write to parse_progress only — no conflict with node_run_semgrep
        return {"parse_results": [], "parse_progress": []}

    files: dict[str, str] = state["file_reader_out"].get("files", {})
    local_events: list[dict] = [
        _event("ast_parser", f"Parsing {len(files)} source files...")
    ]

    parse_results: list[dict] = []

    for filepath, source in files.items():
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == ".py":
                result = parse_python_file(filepath, source)
            elif ext in TREESITTER_EXTENSIONS:
                result = parse_ts_file(filepath, source)
            else:
                continue
        except Exception as exc:
            logger.warning(f"[node_parse_files] error parsing {filepath}: {exc}")
            result = {
                "filepath":    filepath,
                "language":    "unknown",
                "parse_error": str(exc),
                "functions":   [],
                "classes":     [],
                "imports":     [],
                "calls":       [],
                "stats":       {},
            }

        parse_results.append(result)
        local_events.append(_event("ast_parser", f"Parsed {filepath}"))

    local_events.append(_event(
        "ast_parser",
        f"Parsed {len(parse_results)} files",
        {"parsed": len(parse_results),
         "errors": sum(1 for r in parse_results if r.get("parse_error"))},
    ))

    # Write to parse_progress — node_run_semgrep owns semgrep_progress, no conflict
    return {
        "parse_results":  parse_results,
        "parse_progress": local_events,
    }

# ---------------------------------------------------------------------------
# NODE 3 — Run Semgrep
# ---------------------------------------------------------------------------

def node_run_semgrep(state: ScanState) -> dict:
    logger.info("[node_run_semgrep] starting")

    if state.get("scan_error"):
        # Write to semgrep_progress only — no conflict with node_parse_files
        return {"semgrep_out": {}, "semgrep_progress": []}

    repo_path = state["repo_path"]
    rules     = state.get("rules", "auto")

    result = run_semgrep(repo_path, rules=rules)

    sev = result.get("severity_summary", {})
    # Write to semgrep_progress — node_parse_files owns parse_progress, no conflict
    return {
        "semgrep_out":      result,
        "semgrep_progress": [
            _event("semgrep", "Running security scan...", {"rules": rules}),
            _event(
                "semgrep",
                "Semgrep complete",
                {
                    "findings": result.get("stats", {}).get("total_findings", 0),
                    "errors":   sev.get("ERROR", 0),
                    "warnings": sev.get("WARNING", 0),
                },
            ),
        ],
    }

# ---------------------------------------------------------------------------
# NODE 4 — Build call graph
# ---------------------------------------------------------------------------

def node_build_call_graph(state: ScanState) -> dict:
    """Fan-in node: merges parse_progress + semgrep_progress into progress,
    then builds the call graph on top of the now-complete parse_results."""
    logger.info("[node_build_call_graph] starting")

    # Merge the two parallel branches' progress streams into the main list.
    # Both keys are guaranteed to exist because node_parse_files and
    # node_run_semgrep always set them (even on the skip path).
    merged_progress: list[dict] = (
        list(state.get("progress", []))
        + list(state.get("parse_progress", []))
        + list(state.get("semgrep_progress", []))
    )

    if state.get("scan_error"):
        return {
            "call_graph_out": {},
            "progress":       merged_progress,
            "current_stage":  "callgraph_skipped",
        }

    result = build_call_graph(state["parse_results"])

    stats = result.get("stats", {})
    rate  = stats.get("resolution_rate", 0.0)
    merged_progress += [
        _event("call_graph", "Building call graph..."),
        _event(
            "call_graph",
            "Call graph ready",
            {
                "symbols":          stats.get("total_symbols", 0),
                "resolution_rate":  f"{rate:.1%}",
                "circular_imports": stats.get("circular_import_count", 0),
            },
        ),
    ]

    return {
        "call_graph_out": result,
        "progress":       merged_progress,
        "current_stage":  "callgraph_done",
    }

# ---------------------------------------------------------------------------
# NODE 5 — Check findings (decision node)
# ---------------------------------------------------------------------------

def node_check_findings(state: ScanState) -> dict:
    """Pure routing checkpoint — does no heavy work."""
    logger.info("[node_check_findings] evaluating")

    if state.get("scan_error"):
        return {"current_stage": "check_skipped"}

    has_semgrep = len(state["semgrep_out"].get("findings", [])) > 0
    has_ast_flags = any(
        any(pr.get("security_flags", {}).values())
        for pr in state["parse_results"]
        if pr.get("security_flags")
    )
    verdict = "findings" if (has_semgrep or has_ast_flags) else "no_findings"
    logger.info(f"[node_check_findings] verdict={verdict}")

    return {
        "progress": [_event(
            "check_findings",
            "Findings check complete",
            {"has_semgrep": has_semgrep, "has_ast_flags": has_ast_flags, "verdict": verdict},
        )],
        "current_stage": f"check_{verdict}",
    }

def route_findings(state: ScanState) -> str:
    """Conditional edge: decide whether to call the LLM agent."""
    if state.get("scan_error"):
        return "node_no_findings"

    has_semgrep = len(state["semgrep_out"].get("findings", [])) > 0
    has_flags   = any(
        any(pr.get("security_flags", {}).values())
        for pr in state["parse_results"]
        if pr.get("security_flags")
    )
    return "node_agent" if (has_semgrep or has_flags) else "node_no_findings"

# ---------------------------------------------------------------------------
# NODE 6 — LLM agent
# ---------------------------------------------------------------------------

def node_agent(state: ScanState) -> dict:
    logger.info("[node_agent] invoking LLM")

    try:
        agent_out = run_vuln_agent(state)
        agent_out = _normalize_agent_output(agent_out, state)
        logger.info(
            f"[node_agent] LLM returned {len(agent_out.get('findings', []))} findings"
        )
    except Exception as exc:
        logger.error(f"[node_agent] LLM call failed: {exc}")
        agent_out = {
            "findings":             [],
            "summary":              f"LLM analysis failed: {exc}",
            "risk_score":           0.0,
            "most_vulnerable_file": "",
        }

    return {
        "agent_out":  agent_out,
        "progress":   [
            _event("agent", "LLM agent reasoning..."),
            _event("agent", "Analysis complete",
                   {"findings": len(agent_out.get("findings", []))}),
        ],
        "current_stage": "agent_done",
    }

# ---------------------------------------------------------------------------
# NODE 7 — Assemble final report
# ---------------------------------------------------------------------------

def _assemble_report(state: ScanState) -> dict:
    agent_out  = state.get("agent_out", {})
    findings   = agent_out.get("findings", [])

    by_severity: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        sev = str(f.get("severity", "")).upper()
        if sev in by_severity:
            by_severity[sev] += 1

    file_reader_meta = state.get("file_reader_out", {}).get("metadata", {})
    cg               = state.get("call_graph_out", {})
    cg_stats         = cg.get("stats", {})
    now_ts           = datetime.now(timezone.utc).timestamp()
    scan_start       = float(state.get("scan_started_at", now_ts))
    scan_duration_ms = max(0, int((now_ts - scan_start) * 1000))

    return {
        "scan_id":    str(uuid.uuid4()),
        "repo_path":  state["repo_path"],
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "scanned_files": file_reader_meta.get("total_files", 0),
        "scan_duration_ms": scan_duration_ms,
        "stats": {
            "total_files":    file_reader_meta.get("total_files", 0),
            "languages":      file_reader_meta.get("languages_detected", []),
            "total_findings": len(findings),
            "by_severity":    by_severity,
        },
        "findings":    findings,
        "semgrep_raw": state.get("semgrep_out", {}),
        "call_graph_summary": {
            "hotspots":         cg.get("hotspots", []),
            "circular_imports": cg.get("circular_imports", []),
            "resolution_rate":  cg_stats.get("resolution_rate", 0.0),
            "total_symbols":    cg_stats.get("total_symbols", 0),
        },
        "summary":              agent_out.get("summary", ""),
        "risk_score":           float(agent_out.get("risk_score", 0.0)),
        "most_vulnerable_file": agent_out.get("most_vulnerable_file", ""),
        "scan_error":           state.get("scan_error"),
    }


def node_clean_report(state: ScanState) -> dict:
    logger.info("[node_clean_report] assembling final report")

    report = _assemble_report(state)
    return {
        "final_report":  report,
        "progress":      [_event(
            "complete",
            "Scan finished",
            {
                "scan_id":        report["scan_id"],
                "total_findings": report["stats"]["total_findings"],
                "risk_score":     report["risk_score"],
            },
        )],
        "current_stage": "complete",
    }

# ---------------------------------------------------------------------------
# NODE 8 — No findings short-circuit
# ---------------------------------------------------------------------------

def node_no_findings(state: ScanState) -> dict:
    logger.info("[node_no_findings] no findings — skipping LLM")
    return {
        "agent_out": {
            "findings":             [],
            "summary":              "No vulnerabilities found.",
            "risk_score":           0.0,
            "most_vulnerable_file": "",
        },
        "progress":      [_event("agent", "No security findings detected — LLM skipped")],
        "current_stage": "no_findings",
    }

# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    graph = StateGraph(ScanState)

    # Register nodes
    graph.add_node("node_read_files",       node_read_files)
    graph.add_node("node_parse_files",      node_parse_files)
    graph.add_node("node_run_semgrep",      node_run_semgrep)
    graph.add_node("node_build_call_graph", node_build_call_graph)
    graph.add_node("node_check_findings",   node_check_findings)
    graph.add_node("node_agent",            node_agent)
    graph.add_node("node_no_findings",      node_no_findings)
    graph.add_node("node_clean_report",     node_clean_report)

    # START → read files
    graph.add_edge(START, "node_read_files")

    # Parallel fan-out: read → [parse, semgrep]
    graph.add_edge("node_read_files", "node_parse_files")
    graph.add_edge("node_read_files", "node_run_semgrep")

    # Fan-in: both branches → build call graph
    graph.add_edge("node_parse_files",  "node_build_call_graph")
    graph.add_edge("node_run_semgrep",  "node_build_call_graph")

    # Call graph → check findings
    graph.add_edge("node_build_call_graph", "node_check_findings")

    # Conditional: findings? → agent, else → no_findings
    graph.add_conditional_edges(
        "node_check_findings",
        route_findings,
        {
            "node_agent":       "node_agent",
            "node_no_findings": "node_no_findings",
        },
    )

    # Both branches → clean report → END
    graph.add_edge("node_agent",       "node_clean_report")
    graph.add_edge("node_no_findings", "node_clean_report")
    graph.add_edge("node_clean_report", END)

    return graph


# Compile once at module level
_graph         = _build_graph()
COMPILED_GRAPH = _graph.compile()

logger.info("Orchestrator graph compiled successfully")

# ---------------------------------------------------------------------------
# Public API — start_scan()
# ---------------------------------------------------------------------------

async def start_scan(
    repo_path: str,
    rules: str = "auto",
) -> AsyncGenerator[dict, None]:
    """
    Run the full scan DAG and yield progress events + final report.
    Designed to be consumed by a FastAPI SSE endpoint.

    Usage in FastAPI:
        async for event in start_scan(repo_path):
            yield f"data: {json.dumps(event)}\\n\\n"

    Args:
        repo_path: Absolute path to the target repository.
        rules:     Semgrep ruleset string (default "auto").

    Yields:
        Progress event dicts, then a final_report event as the last item.
    """
    initial_state: ScanState = {
        "repo_path":        repo_path,
        "rules":            rules,
        "file_reader_out":  {},
        "parse_results":    [],
        "semgrep_out":      {},
        "call_graph_out":   {},
        "agent_out":        {},
        "final_report":     {},
        # Parallel branch keys — written exclusively by their respective nodes
        "parse_progress":   [],
        "semgrep_progress": [],
        # Main progress list — seeded empty, node_build_call_graph merges into it
        "progress":         [],
        "current_stage":    "init",
        "scan_error":       None,
        "scan_started_at":  datetime.now(timezone.utc).timestamp(),
    }

    # Accumulate progress events across all streamed chunks.  We track the
    # high-water mark so we yield each event exactly once.
    accumulated_progress: list[dict] = []
    last_state: dict = {}

    try:
        async for chunk in COMPILED_GRAPH.astream(initial_state):
            # chunk == {node_name: partial_state_dict}
            for node_name, partial in chunk.items():
                if not isinstance(partial, dict):
                    continue
                last_state.update(partial)

                # Collect whichever progress keys this node updated
                for key in ("progress", "parse_progress", "semgrep_progress"):
                    new_events = partial.get(key, [])
                    for event in new_events:
                        if event not in accumulated_progress:
                            accumulated_progress.append(event)
                            yield event
    except Exception as exc:
        logger.error(f"[start_scan] graph execution error: {exc}", exc_info=True)
        yield _event("error", f"Scan failed: {exc}", {"error": str(exc)})

    # Always yield the final report as the last event
    yield {
        "stage":  "final_report",
        "report": last_state.get("final_report", {}),
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    import logging as _logging
    import sys
    from pathlib import Path

    from dotenv import load_dotenv
    # Walk up from this file to find the backend root and load .env
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    _logging.basicConfig(
        level=_logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s",
    )

    async def main() -> None:
        path = sys.argv[1] if len(sys.argv) > 1 else "."
        print(f"Scanning: {path}\n{'=' * 60}")
        async for event in start_scan(path):
            print(json.dumps(event, indent=2, default=str))

    asyncio.run(main())
