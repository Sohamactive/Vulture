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


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


SEVERITY_RANK: dict[str, int] = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}

SEVERITY_PENALTY: dict[str, int] = {
    "CRITICAL": 30,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5,
}

REACHABILITY_VALUES = (
    "publicly reachable",
    "auth-protected",
    "internal only",
    "not externally exposed",
)

EXPLOITABILITY_LEVEL_WEIGHT: dict[str, int] = {
    "CRITICAL": 40,
    "HIGH": 28,
    "MEDIUM": 16,
    "LOW": 8,
}

REACHABILITY_WEIGHT: dict[str, int] = {
    "publicly reachable": 30,
    "auth-protected": 18,
    "internal only": 8,
    "not externally exposed": 2,
}


def _normalize_severity(value: Any) -> str:
    severity = str(value or "MEDIUM").strip().upper()
    if severity in {"ERROR", "CRITICAL"}:
        return "CRITICAL"
    if severity in {"WARNING", "WARN", "HIGH"}:
        return "HIGH"
    if severity in {"INFO", "LOW"}:
        return "LOW"
    if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
        return "MEDIUM"
    return severity


def _normalize_level(value: Any, *, default: str = "MEDIUM") -> str:
    text = str(value or "").upper()
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if level in text:
            return level
    return default


def _normalize_reachability(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    if "public" in raw:
        return "publicly reachable"
    if "auth" in raw or "protected" in raw:
        return "auth-protected"
    if "internal" in raw:
        return "internal only"
    if "not externally" in raw or "not exposed" in raw:
        return "not externally exposed"
    return None


def _normalize_line_numbers(value: Any, line_start: int | None, line_end: int | None) -> list[int]:
    normalized: list[int] = []
    if isinstance(value, list):
        for item in value:
            item_int = _coerce_int(item)
            if item_int is not None and item_int > 0:
                normalized.append(item_int)
    if normalized:
        return sorted(set(normalized))
    if line_start is None:
        return []
    if line_end is not None and line_end >= line_start:
        return list(range(line_start, line_end + 1))
    return [line_start]


def _normalize_exploit_chain(value: Any) -> list[str]:
    if isinstance(value, list):
        chain = [str(item).strip() for item in value if str(item).strip()]
        return chain[:6]
    if isinstance(value, str):
        parts = re.split(r"\s*(?:->|→|=>|\|)\s*", value)
        chain = [part.strip(" -") for part in parts if part.strip(" -")]
        return chain[:6]
    return []


def _extract_context_snippet(
    source: str,
    line_start: int | None,
    line_end: int | None,
    *,
    context: int = 2,
) -> str:
    if not source:
        return ""
    lines = source.replace("\r\n", "\n").split("\n")
    if not lines:
        return ""
    if line_start is None:
        max_lines = min(len(lines), 8)
        return "\n".join(f"{idx + 1:>4} | {lines[idx]}" for idx in range(max_lines))

    start = max(1, line_start - context)
    end = line_start + context
    if line_end is not None and line_end >= line_start:
        end = line_end + context
    end = min(len(lines), end)
    if start > end:
        start = end
    snippet_lines = []
    for idx in range(start, end + 1):
        snippet_lines.append(f"{idx:>4} | {lines[idx - 1]}")
    return "\n".join(snippet_lines)


def _find_parse_result(filepath: str | None, parse_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not filepath:
        return None
    normalized = filepath.replace("\\", "/")
    for pr in parse_results:
        pr_path = str(pr.get("filepath") or "").replace("\\", "/")
        if pr_path == normalized or pr_path.endswith(normalized) or normalized.endswith(pr_path):
            return pr
    return None


def _has_ast_security_evidence(parse_result: dict[str, Any] | None) -> bool:
    if not parse_result:
        return False
    flags = parse_result.get("security_flags") or {}
    if not isinstance(flags, dict):
        return False
    return any(bool(v) for v in flags.values())


def _infer_reachability(
    finding: dict[str, Any],
    parse_result: dict[str, Any] | None,
    call_graph_out: dict[str, Any],
) -> str:
    from_finding = _normalize_reachability(finding.get("reachability"))
    if from_finding:
        return from_finding

    filepath = str(
        finding.get("filepath")
        or finding.get("file_path")
        or ""
    ).lower()
    title = str(finding.get("title") or "").lower()
    description = str(finding.get("description") or "").lower()
    text = f"{filepath} {title} {description}"

    if any(key in filepath for key in ("test/", "/tests/", "spec.", "mock", "fixture")):
        return "not externally exposed"

    route_keys = ("api", "route", "controller", "handler", "endpoint", "view", "gateway")
    auth_keys = ("auth", "login", "token", "session", "oauth")
    internal_keys = ("worker", "job", "cron", "internal", "service", "admin")

    if any(k in text for k in route_keys):
        return "publicly reachable"
    if any(k in text for k in auth_keys):
        return "auth-protected"
    if any(k in filepath for k in internal_keys):
        return "internal only"

    if parse_result:
        for fn in parse_result.get("functions", []):
            decorators = [str(d).lower() for d in fn.get("decorators", [])]
            if any(("route" in d or "get" in d or "post" in d or "websocket" in d) for d in decorators):
                if any("auth" in d for d in decorators):
                    return "auth-protected"
                return "publicly reachable"

    call_edges = call_graph_out.get("call_edges", [])
    for edge in call_edges:
        caller_file = str(edge.get("caller_file") or "").lower()
        callee_file = str(edge.get("callee_file") or "").lower()
        if filepath and filepath not in (caller_file, callee_file):
            continue
        if any(k in caller_file for k in route_keys):
            return "publicly reachable"
        if any(k in caller_file for k in auth_keys):
            return "auth-protected"

    return "internal only"


def _infer_exploitability(severity: str, reachability: str, value: Any) -> str:
    existing = str(value or "").strip()
    level = _normalize_level(existing, default=severity)
    if not existing:
        reason = {
            "publicly reachable": "directly exposed to external callers",
            "auth-protected": "reachable after authentication",
            "internal only": "limited to internal execution paths",
            "not externally exposed": "no external entry point detected",
        }.get(reachability, "context-based estimate")
        return f"{level} -- {reason}"
    return existing


def _infer_business_impact(owasp: str | None, severity: str, value: Any) -> str:
    existing = str(value or "").strip()
    if existing:
        return existing
    if owasp == "A01:Access Control":
        return "Privilege escalation and unauthorized data access."
    if owasp == "A03:Injection":
        return "Data tampering or database compromise."
    if owasp == "A07:Auth":
        return "Account takeover and lateral movement."
    if severity == "CRITICAL":
        return "Potential full service compromise."
    if severity == "HIGH":
        return "High-impact confidentiality or integrity loss."
    if severity == "MEDIUM":
        return "Business logic abuse or scoped data exposure."
    return "Limited business impact."


def _infer_false_positive_risk(confidence_score: int, value: Any) -> str:
    existing = str(value or "").strip()
    if existing:
        return existing
    if confidence_score >= 80:
        return "LOW -- multiple supporting signals."
    if confidence_score >= 55:
        return "MEDIUM -- partial corroboration."
    return "HIGH -- weak supporting evidence."


def _estimate_taint_flow(
    finding: dict[str, Any],
    call_graph_out: dict[str, Any],
) -> bool:
    snippet = str(finding.get("code_snippet") or "").lower()
    title = str(finding.get("title") or "").lower()
    callee_tokens = " ".join(str(edge.get("callee") or "").lower() for edge in call_graph_out.get("call_edges", []))
    taint_terms = ("request", "params", "query", "body", "input", "sink", "execute", "eval", "os.system")
    return any(term in snippet or term in title or term in callee_tokens for term in taint_terms)


def _confidence_from_evidence(
    finding: dict[str, Any],
    semgrep_match: dict[str, Any] | None,
    parse_result: dict[str, Any] | None,
    call_graph_out: dict[str, Any],
) -> tuple[int, dict[str, bool]]:
    semgrep_confirmed = semgrep_match is not None
    ast_evidence = _has_ast_security_evidence(parse_result)
    contextual_evidence = _normalize_reachability(finding.get("reachability")) in {
        "publicly reachable",
        "auth-protected",
    }
    taint_flow = _estimate_taint_flow(finding, call_graph_out)

    score = 20
    if semgrep_confirmed:
        score += 40
    if ast_evidence:
        score += 20
    if contextual_evidence:
        score += 10
    if taint_flow:
        score += 10

    provided = _coerce_int(finding.get("confidence_score"))
    if provided is not None:
        score = int((score * 0.7) + (max(0, min(100, provided)) * 0.3))
    factors = {
        "semgrep_confirmation": semgrep_confirmed,
        "ast_evidence": ast_evidence,
        "contextual_evidence": contextual_evidence,
        "taint_flow_existence": taint_flow,
    }
    return max(0, min(100, score)), factors


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


def _finding_priority_score(finding: dict[str, Any]) -> int:
    severity = _normalize_severity(finding.get("severity"))
    exploitability_level = _normalize_level(finding.get("exploitability"), default=severity)
    reachability = _normalize_reachability(finding.get("reachability")) or "internal only"
    impact_level = _normalize_level(finding.get("business_impact"), default=severity)
    confidence_score = _coerce_int(finding.get("confidence_score")) or 0
    return (
        SEVERITY_RANK.get(severity, 2) * 20
        + EXPLOITABILITY_LEVEL_WEIGHT.get(exploitability_level, 16)
        + REACHABILITY_WEIGHT.get(reachability, 8)
        + SEVERITY_RANK.get(impact_level, 2) * 8
        + int(confidence_score * 0.2)
    )


def _compute_remediation_priority(finding: dict[str, Any]) -> str:
    score = _finding_priority_score(finding)
    if score >= 140:
        return "P0 -- immediate remediation required."
    if score >= 110:
        return "P1 -- fix in current sprint."
    if score >= 80:
        return "P2 -- schedule planned remediation."
    return "P3 -- monitor and harden over time."


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for finding in findings:
        key = (
            str(finding.get("title") or "").strip().lower(),
            str(finding.get("cwe_id") or ""),
            str(finding.get("owasp_category") or ""),
            str(finding.get("severity") or "MEDIUM"),
        )
        grouped.setdefault(key, []).append(finding)

    deduped: list[dict[str, Any]] = []
    for index, group in enumerate(grouped.values(), start=1):
        group_sorted = sorted(group, key=_finding_priority_score, reverse=True)
        primary = dict(group_sorted[0])
        related_locations = []
        for item in group_sorted:
            related_locations.append(
                {
                    "filepath": item.get("filepath"),
                    "line_start": item.get("line_start"),
                    "line_end": item.get("line_end"),
                    "severity": item.get("severity"),
                }
            )
        primary["dedupe_group"] = f"FG-{index:03d}"
        primary["related_locations"] = related_locations
        primary["repeated_instances"] = len(group_sorted)
        deduped.append(primary)
    return deduped


def _build_fallback_findings(state: ScanState) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in state.get("semgrep_out", {}).get("findings", []):
        if not isinstance(item, dict):
            continue
        severity = _normalize_severity(item.get("severity"))
        findings.append(
            {
                "severity": severity,
                "title": item.get("rule_name") or item.get("rule_id") or "Semgrep finding",
                "description": item.get("message") or "Semgrep rule triggered.",
                "filepath": item.get("filepath"),
                "line_start": _coerce_int(item.get("line_start")),
                "line_end": _coerce_int(item.get("line_end")),
                "code_snippet": item.get("code_snippet"),
                "cwe": _normalize_cwe(item.get("cwe")),
                "owasp_category": _canonical_owasp(item.get("owasp")) or _infer_owasp_from_text(
                    f"{item.get('rule_name', '')} {item.get('message', '')}"
                ),
                "detection_source": "semgrep",
                "fix": item.get("fix") or "Review and patch vulnerable pattern.",
            }
        )
    return findings


def _normalize_agent_output(agent_out: dict[str, Any], state: ScanState) -> dict[str, Any]:
    semgrep_findings: list[dict[str, Any]] = state.get("semgrep_out", {}).get("findings", [])
    parse_results: list[dict[str, Any]] = state.get("parse_results", [])
    call_graph_out: dict[str, Any] = state.get("call_graph_out", {})
    source_files: dict[str, str] = state.get("file_reader_out", {}).get("files", {})

    raw_findings = agent_out.get("findings", [])
    if not isinstance(raw_findings, list):
        raw_findings = []
    if not raw_findings and semgrep_findings:
        raw_findings = _build_fallback_findings(state)

    normalized_findings: list[dict[str, Any]] = []

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

        severity = _normalize_severity(finding.get("severity"))
        parse_result = _find_parse_result(str(filepath) if filepath else None, parse_results)
        reachability = _infer_reachability(finding, parse_result, call_graph_out)
        exploitability = _infer_exploitability(
            severity,
            reachability,
            finding.get("exploitability"),
        )

        line_numbers = _normalize_line_numbers(
            finding.get("line_numbers"),
            line_start,
            line_end,
        )
        source_text = source_files.get(str(filepath), "") if filepath else ""
        snippet = str(finding.get("code_snippet") or "").strip()
        context_snippet = _extract_context_snippet(source_text, line_start, line_end)
        if not snippet:
            snippet = context_snippet
        elif context_snippet and "|" not in snippet:
            snippet = context_snippet

        confidence_score, confidence_factors = _confidence_from_evidence(
            finding=finding,
            semgrep_match=semgrep_match,
            parse_result=parse_result,
            call_graph_out=call_graph_out,
        )
        business_impact = _infer_business_impact(
            owasp_category,
            severity,
            finding.get("business_impact"),
        )
        false_positive_risk = _infer_false_positive_risk(
            confidence_score,
            finding.get("false_positive_risk"),
        )
        exploit_chain = _normalize_exploit_chain(finding.get("exploit_chain"))
        attack_scenario = str(finding.get("attack_scenario") or "").strip()
        if not attack_scenario:
            attack_scenario = (
                f"An attacker may exploit {str(finding.get('title') or 'this weakness').lower()} "
                f"to impact target functionality through {reachability} path."
            )

        normalized = dict(finding)
        normalized["filepath"] = filepath
        normalized["file_path"] = filepath
        normalized["line_start"] = line_start
        normalized["line_end"] = line_end
        normalized["line_numbers"] = line_numbers
        normalized["owasp_category"] = owasp_category
        normalized["cwe"] = cwe_value
        normalized["cwe_id"] = cwe_value
        normalized["severity"] = severity
        normalized["code_snippet"] = snippet
        normalized["reachability"] = reachability
        normalized["exploitability"] = exploitability
        normalized["confidence_score"] = confidence_score
        normalized["confidence_factors"] = confidence_factors
        normalized["business_impact"] = business_impact
        normalized["false_positive_risk"] = false_positive_risk
        normalized["attack_scenario"] = attack_scenario
        normalized["exploit_chain"] = exploit_chain
        normalized["remediation_priority"] = str(
            finding.get("remediation_priority") or ""
        ).strip() or _compute_remediation_priority(normalized)
        normalized["detection_source"] = (
            str(finding.get("detection_source") or "").strip()
            or ("semgrep+ai" if semgrep_match else "ai")
        )

        normalized_findings.append(normalized)

    deduped = _dedupe_findings(normalized_findings)
    deduped.sort(key=_finding_priority_score, reverse=True)
    agent_out["findings"] = deduped
    return agent_out


def _build_security_score_breakdown(
    findings: list[dict[str, Any]],
    parse_results: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {
        "Authentication Security": [],
        "Input Validation": [],
        "Dependency Security": [],
        "Transport Security": [],
        "Configuration Security": [],
        "Secrets Management": [],
    }
    hardcoded_secret_files = 0
    for pr in parse_results:
        flags = pr.get("security_flags") or {}
        if isinstance(flags, dict) and flags.get("has_hardcoded_str"):
            hardcoded_secret_files += 1

    for finding in findings:
        owasp = str(finding.get("owasp_category") or "")
        text = f"{finding.get('title', '')} {finding.get('description', '')}".lower()
        if owasp in {"A07:Auth", "A01:Access Control"} or "auth" in text or "token" in text:
            buckets["Authentication Security"].append(finding)
        if owasp == "A03:Injection" or any(k in text for k in ("injection", "xss", "sanitize", "validation")):
            buckets["Input Validation"].append(finding)
        if owasp in {"A06:Outdated", "A08:Integrity"} or any(k in text for k in ("dependency", "package", "supply chain")):
            buckets["Dependency Security"].append(finding)
        if owasp == "A02:Crypto" or any(k in text for k in ("tls", "ssl", "http://", "encryption", "crypto")):
            buckets["Transport Security"].append(finding)
        if owasp in {"A05:Config", "A09:Logging", "A04:Design"} or any(k in text for k in ("misconfig", "config", "header", "cors")):
            buckets["Configuration Security"].append(finding)
        if any(k in text for k in ("secret", "password", "key", "credential")) or str(finding.get("cwe_id") or "") in {"CWE-798", "CWE-259"}:
            buckets["Secrets Management"].append(finding)

    if hardcoded_secret_files > 0:
        # Ensure parser evidence contributes even when findings are sparse.
        buckets["Secrets Management"] += [{} for _ in range(hardcoded_secret_files)]

    breakdown: dict[str, dict[str, Any]] = {}
    for category, items in buckets.items():
        penalty = 0
        for item in items:
            penalty += SEVERITY_PENALTY.get(_normalize_severity(item.get("severity")), 8)
        score = max(0, 100 - penalty)
        if not items:
            explanation = "No significant issues detected for this category."
        else:
            top_sev = _normalize_severity(items[0].get("severity"))
            explanation = f"{len(items)} issue(s) mapped; highest severity {top_sev}."
        breakdown[category] = {
            "score": score,
            "explanation": explanation,
        }
    return breakdown


def _build_repository_intelligence(state: ScanState) -> dict[str, Any]:
    parse_results = state.get("parse_results", [])
    file_reader_meta = state.get("file_reader_out", {}).get("metadata", {})
    call_graph = state.get("call_graph_out", {})
    call_graph_stats = call_graph.get("stats", {})

    parsed_files = len(parse_results)
    hotspot_entries = call_graph.get("hotspots", [])[:8]
    hotspot_paths = [str(item.get("filepath")) for item in hotspot_entries if item.get("filepath")]
    unresolved = call_graph.get("unresolved_calls", [])

    return {
        "files_analyzed": int(file_reader_meta.get("total_files", parsed_files)),
        "parsed_files": parsed_files,
        "symbols_indexed": int(call_graph_stats.get("total_symbols", 0)),
        "call_edges": int(call_graph_stats.get("total_call_edges", 0)),
        "hotspots": hotspot_paths,
        "circular_imports": call_graph.get("circular_imports", []),
        "unresolved_calls": unresolved[:10],
        "resolution_rate": float(call_graph_stats.get("resolution_rate", 0.0)),
    }


def _build_attack_surface_overview(state: ScanState) -> dict[str, Any]:
    parse_results = state.get("parse_results", [])
    api_routes: set[str] = set()
    auth_endpoints: set[str] = set()
    websocket_endpoints: set[str] = set()
    file_upload_handlers: set[str] = set()
    external_requests: set[str] = set()
    database_connectors: set[str] = set()
    filesystem_access_points: set[str] = set()

    for pr in parse_results:
        filepath = str(pr.get("filepath") or "")
        filepath_low = filepath.lower()
        for fn in pr.get("functions", []):
            fn_name = str(fn.get("name") or "")
            fn_name_low = fn_name.lower()
            decorators = [str(d).lower() for d in fn.get("decorators", [])]
            calls = [str(c).lower() for c in fn.get("calls_made", [])]
            combined = " ".join(calls + decorators + [filepath_low, fn_name_low])

            if any(key in combined for key in ("route", "get(", "post(", "put(", "delete(", "api")):
                api_routes.add(f"{filepath}:{fn_name}")
            if any(key in combined for key in ("auth", "login", "jwt", "token", "oauth")):
                auth_endpoints.add(f"{filepath}:{fn_name}")
            if "websocket" in combined or "ws" in fn_name_low:
                websocket_endpoints.add(f"{filepath}:{fn_name}")
            if any(key in combined for key in ("upload", "multipart", "save_file", "file.write")):
                file_upload_handlers.add(f"{filepath}:{fn_name}")
            if any(key in combined for key in ("requests.", "httpx.", "axios", "fetch(", "urlopen", "urllib")):
                external_requests.add(f"{filepath}:{fn_name}")
            if any(key in combined for key in ("cursor.execute", ".query(", ".connect(", "sqlalchemy", "pymongo", "redis")):
                database_connectors.add(f"{filepath}:{fn_name}")
            if any(key in combined for key in ("open(", "os.path", "pathlib", "shutil", "fs.")):
                filesystem_access_points.add(f"{filepath}:{fn_name}")

    return {
        "api_routes": sorted(api_routes),
        "auth_endpoints": sorted(auth_endpoints),
        "websocket_endpoints": sorted(websocket_endpoints),
        "file_upload_handlers": sorted(file_upload_handlers),
        "external_requests": sorted(external_requests),
        "database_connectors": sorted(database_connectors),
        "filesystem_access_points": sorted(filesystem_access_points),
    }


def _build_file_risk_heatmap(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_file: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        fp = str(finding.get("filepath") or finding.get("file_path") or "").strip()
        if not fp:
            continue
        by_file.setdefault(fp, []).append(finding)

    heatmap: list[dict[str, Any]] = []
    for filepath, file_findings in by_file.items():
        dominant = max(
            (str(f.get("owasp_category") or "Uncategorized") for f in file_findings),
            key=lambda category: sum(1 for f in file_findings if str(f.get("owasp_category") or "Uncategorized") == category),
            default="Uncategorized",
        )
        highest = max(file_findings, key=_finding_priority_score)
        heatmap.append(
            {
                "filepath": filepath,
                "vulnerability_count": len(file_findings),
                "dominant_risk_type": dominant,
                "highest_severity": _normalize_severity(highest.get("severity")),
            }
        )
    heatmap.sort(
        key=lambda item: (
            -item.get("vulnerability_count", 0),
            -SEVERITY_RANK.get(str(item.get("highest_severity") or "LOW"), 1),
        )
    )
    return heatmap[:12]


def _build_reachability_analysis(findings: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {key: 0 for key in REACHABILITY_VALUES}
    examples: dict[str, list[str]] = {key: [] for key in REACHABILITY_VALUES}
    for finding in findings:
        reachability = _normalize_reachability(finding.get("reachability")) or "internal only"
        counts[reachability] += 1
        if len(examples[reachability]) < 3:
            examples[reachability].append(str(finding.get("title") or "Untitled finding"))
    return {
        "counts": counts,
        "examples": examples,
    }


def _build_exploit_chains(findings: list[dict[str, Any]]) -> list[list[str]]:
    chains: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for finding in findings:
        chain = _normalize_exploit_chain(finding.get("exploit_chain"))
        if len(chain) < 2:
            continue
        key = tuple(chain)
        if key in seen:
            continue
        seen.add(key)
        chains.append(chain)
    return chains[:8]


def _build_attack_scenarios(findings: list[dict[str, Any]], agent_out: dict[str, Any]) -> list[str]:
    from_agent = agent_out.get("attack_scenarios")
    scenarios = _coerce_str_list(from_agent) if isinstance(from_agent, list) else []
    if scenarios:
        return scenarios[:10]

    synthesized: list[str] = []
    for finding in findings[:10]:
        scenario = str(finding.get("attack_scenario") or "").strip()
        if scenario:
            synthesized.append(scenario)
            continue
        title = str(finding.get("title") or "security weakness").lower()
        reachability = _normalize_reachability(finding.get("reachability")) or "internal only"
        synthesized.append(
            f"An attacker may abuse {title} through a {reachability} path to compromise sensitive operations."
        )
    return synthesized


def _build_executive_risk_verdict(
    findings: list[dict[str, Any]],
    agent_out: dict[str, Any],
) -> dict[str, Any]:
    from_agent = agent_out.get("executive_risk_verdict")
    if isinstance(from_agent, dict):
        posture = str(from_agent.get("overall_risk_posture") or "").strip()
        critical = str(from_agent.get("most_critical_risk_area") or "").strip()
        remote = str(from_agent.get("remotely_exploitable_findings") or "").strip()
        if posture and critical and remote:
            return {
                "overall_risk_posture": posture,
                "most_critical_risk_area": critical,
                "remotely_exploitable_findings": remote,
            }

    critical_count = sum(1 for f in findings if _normalize_severity(f.get("severity")) == "CRITICAL")
    high_count = sum(1 for f in findings if _normalize_severity(f.get("severity")) == "HIGH")
    public_reach = sum(
        1
        for f in findings
        if _normalize_reachability(f.get("reachability")) == "publicly reachable"
    )

    if critical_count > 0 or public_reach >= 2:
        posture = "High"
    elif high_count > 0:
        posture = "Moderate"
    else:
        posture = "Low"

    categories: dict[str, int] = {}
    for finding in findings:
        cat = str(finding.get("owasp_category") or "Uncategorized")
        categories[cat] = categories.get(cat, 0) + 1
    top_category = max(categories, key=categories.get) if categories else "No dominant category"
    remote = "Likely yes" if public_reach > 0 else "Not evident from static evidence"

    return {
        "overall_risk_posture": posture,
        "most_critical_risk_area": top_category,
        "remotely_exploitable_findings": remote,
    }


def _build_ai_security_assessment(agent_out: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    from_agent = agent_out.get("ai_security_assessment")
    if isinstance(from_agent, dict):
        summary = str(from_agent.get("repository_wide_summary") or "").strip()
        top_risks = _coerce_str_list(from_agent.get("top_risk_categories"))
        vectors = _coerce_str_list(from_agent.get("likely_attack_vectors"))
        weaknesses = _coerce_str_list(from_agent.get("architectural_weaknesses"))
        if summary:
            return {
                "repository_wide_summary": summary,
                "top_risk_categories": top_risks[:6],
                "likely_attack_vectors": vectors[:8],
                "architectural_weaknesses": weaknesses[:8],
            }

    top_risk_counts: dict[str, int] = {}
    vectors: set[str] = set()
    weaknesses: set[str] = set()
    for finding in findings:
        cat = str(finding.get("owasp_category") or "Uncategorized")
        top_risk_counts[cat] = top_risk_counts.get(cat, 0) + 1
        text = f"{finding.get('title', '')} {finding.get('description', '')}".lower()
        if any(key in text for key in ("token", "auth", "session")):
            vectors.add("Authentication bypass or token abuse")
            weaknesses.add("Trust boundary enforcement is inconsistent")
        if any(key in text for key in ("injection", "query", "execute", "eval")):
            vectors.add("Input-driven injection into sensitive sinks")
            weaknesses.add("Input normalization and sink hardening are uneven")
        if any(key in text for key in ("config", "cors", "header", "exposed")):
            vectors.add("Misconfiguration abuse from external clients")
            weaknesses.add("Security configuration drift across services")

    sorted_categories = sorted(top_risk_counts.items(), key=lambda item: item[1], reverse=True)
    category_names = [item[0] for item in sorted_categories[:4]]
    return {
        "repository_wide_summary": str(agent_out.get("summary") or "Repository contains actionable security weaknesses."),
        "top_risk_categories": category_names,
        "likely_attack_vectors": sorted(vectors)[:8],
        "architectural_weaknesses": sorted(weaknesses)[:8],
    }


def _build_risk_prioritization(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prioritized: list[dict[str, Any]] = []
    for finding in sorted(findings, key=_finding_priority_score, reverse=True):
        prioritized.append(
            {
                "title": finding.get("title"),
                "severity": _normalize_severity(finding.get("severity")),
                "exploitability": finding.get("exploitability"),
                "reachability": finding.get("reachability"),
                "business_impact": finding.get("business_impact"),
                "remediation_priority": finding.get("remediation_priority"),
                "filepath": finding.get("filepath"),
                "line_start": finding.get("line_start"),
                "priority_score": _finding_priority_score(finding),
            }
        )
    return prioritized


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
        agent_out = _normalize_agent_output(agent_out, state)

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
    agent_out = state.get("agent_out", {})
    findings = agent_out.get("findings", [])
    if not isinstance(findings, list):
        findings = []
    findings = sorted(findings, key=_finding_priority_score, reverse=True)

    by_severity: dict[str, int] = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for finding in findings:
        sev = _normalize_severity(finding.get("severity"))
        by_severity[sev] += 1

    file_reader_meta = state.get("file_reader_out", {}).get("metadata", {})
    cg = state.get("call_graph_out", {})
    cg_stats = cg.get("stats", {})
    now_ts = datetime.now(timezone.utc).timestamp()
    scan_start = float(state.get("scan_started_at", now_ts))
    scan_duration_ms = max(0, int((now_ts - scan_start) * 1000))

    risk_score = _coerce_float(agent_out.get("risk_score"))
    if risk_score is None:
        derived_risk = (
            by_severity["CRITICAL"] * 2.4
            + by_severity["HIGH"] * 1.5
            + by_severity["MEDIUM"] * 0.7
            + by_severity["LOW"] * 0.3
        )
        risk_score = max(0.0, min(10.0, derived_risk))
    else:
        risk_score = max(0.0, min(10.0, risk_score))

    repository_intelligence = _build_repository_intelligence(state)
    attack_surface = _build_attack_surface_overview(state)
    score_breakdown = _build_security_score_breakdown(findings, state.get("parse_results", []))
    heatmap = _build_file_risk_heatmap(findings)
    reachability_analysis = _build_reachability_analysis(findings)
    exploit_chains = _build_exploit_chains(findings)
    attack_scenarios = _build_attack_scenarios(findings, agent_out)
    executive_verdict = _build_executive_risk_verdict(findings, agent_out)
    ai_assessment = _build_ai_security_assessment(agent_out, findings)
    risk_prioritization = _build_risk_prioritization(findings)

    finding_deduplication = [
        {
            "group": finding.get("dedupe_group"),
            "title": finding.get("title"),
            "instances": int(finding.get("repeated_instances", 1)),
            "locations": finding.get("related_locations", []),
        }
        for finding in findings
    ]

    privacy_processing = {
        "local_parsing_first": True,
        "local_static_analysis": True,
        "bedrock_inference_used": True,
        "bedrock_training_policy": (
            "AWS Bedrock inference is used. Customer data is not used to train foundation models."
        ),
    }

    return {
        "scan_id": str(uuid.uuid4()),
        "repo_path": state["repo_path"],
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "scanned_files": file_reader_meta.get("total_files", 0),
        "scan_duration_ms": scan_duration_ms,
        "stats": {
            "total_files": file_reader_meta.get("total_files", 0),
            "languages": file_reader_meta.get("languages_detected", []),
            "total_findings": len(findings),
            "by_severity": by_severity,
        },
        "findings": findings,
        "semgrep_raw": state.get("semgrep_out", {}),
        "call_graph_summary": {
            "hotspots": cg.get("hotspots", []),
            "circular_imports": cg.get("circular_imports", []),
            "resolution_rate": cg_stats.get("resolution_rate", 0.0),
            "total_symbols": cg_stats.get("total_symbols", 0),
        },
        "summary": agent_out.get("summary", ""),
        "risk_score": float(risk_score),
        "most_vulnerable_file": agent_out.get("most_vulnerable_file", ""),
        "executive_risk_verdict": executive_verdict,
        "ai_security_assessment": ai_assessment,
        "security_score_breakdown": score_breakdown,
        "repository_intelligence": repository_intelligence,
        "attack_surface_overview": attack_surface,
        "file_risk_heatmap": heatmap,
        "attack_scenarios": attack_scenarios,
        "reachability_analysis": reachability_analysis,
        "exploit_chains": exploit_chains,
        "finding_deduplication": finding_deduplication,
        "privacy_processing": privacy_processing,
        "risk_prioritization": risk_prioritization,
        "scan_error": state.get("scan_error"),
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
    logger.info("[node_no_findings] no findings - skipping LLM")
    return {
        "agent_out": {
            "findings": [],
            "summary": "No vulnerabilities found.",
            "risk_score": 0.0,
            "most_vulnerable_file": "",
            "executive_risk_verdict": {
                "overall_risk_posture": "Low",
                "most_critical_risk_area": "No dominant risk area detected",
                "remotely_exploitable_findings": "Not evident",
            },
            "ai_security_assessment": {
                "repository_wide_summary": "No actionable findings from current static and AI-assisted analysis.",
                "top_risk_categories": [],
                "likely_attack_vectors": [],
                "architectural_weaknesses": [],
            },
            "attack_scenarios": [],
        },
        "progress": [_event("agent", "No security findings detected - LLM skipped")],
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
