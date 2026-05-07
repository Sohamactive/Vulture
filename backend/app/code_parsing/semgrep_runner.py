"""
semgrep_runner.py
Run Semgrep as a subprocess against a target directory or
single file, parse its JSON output, and return structured
findings for the LLM agent to reason over.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
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
# Helpers
# ---------------------------------------------------------------------------

def _error_result(
    target_path: str | Path,
    rules: str,
    run_error: str,
    semgrep_available: bool = True,
) -> dict:
    return {
        "tool": "semgrep",
        "target": str(target_path),
        "rules_used": rules,
        "semgrep_available": semgrep_available,
        "run_error": run_error,
        "findings": [],
        "severity_summary": {"ERROR": 0, "WARNING": 0, "INFO": 0},
        "semgrep_errors": [],
        "stats": {
            "total_findings": 0,
            "returned_findings": 0,
            "files_scanned": 0,
            "rules_run": 0,
            "scan_time_seconds": 0.0,
        },
    }

def _make_relative(path: str, base: Path) -> str:
    try:
        return str(Path(path).relative_to(base))
    except ValueError:
        return path

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_semgrep(
    target_path: str | Path,
    rules: str = "auto",
    timeout_seconds: int = 30,
    max_findings: int = 50,
) -> dict:
    target_path_obj = Path(target_path)
    target_str = str(target_path_obj)

    # STEP 1 — Availability check
    semgrep_path = shutil.which("semgrep")
    if semgrep_path is None:
        return _error_result(
            target_str, rules,
            semgrep_available=False,
            run_error="semgrep not found in PATH — install with: uv add semgrep"
        )

    # STEP 2 — Build command
    cmd = [
        "semgrep",
        "--json",
        "--quiet",
        "--timeout", str(timeout_seconds),
        "--max-target-bytes", "5000000",
        "--no-git-ignore",
        "--exclude", "node_modules",
        "--exclude", ".venv",
        "--exclude", "__pycache__",
        "--config", rules,
        target_str,
    ]
    logger.info(f"Running semgrep: {' '.join(cmd)}")

    # STEP 3 — Run subprocess
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        logger.warning(f"{target_str}: semgrep timed out after 300s")
        return _error_result(target_str, rules, run_error="semgrep timed out after 300s")
    except FileNotFoundError:
        logger.error(f"{target_str}: semgrep binary not found")
        return _error_result(target_str, rules, run_error="semgrep binary not found")
    except Exception as exc:
        logger.error(f"{target_str}: semgrep subprocess error: {exc}")
        return _error_result(target_str, rules, run_error=str(exc))

    # STEP 4 — Parse JSON
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        stderr_hint = (proc.stderr or "")[:500]
        msg = f"failed to parse semgrep JSON output. stderr: {stderr_hint}"
        logger.warning(f"{target_str}: {msg}")
        return _error_result(target_str, rules, run_error=msg)

    # STEP 5 — Extract findings
    raw_findings = data.get("results", [])
    findings_list = []
    
    for item in raw_findings:
        try:
            extra = item.get("extra", {})
            meta = extra.get("metadata", {}) or {}

            cwe = meta.get("cwe", [])
            if isinstance(cwe, str):
                cwe = [cwe]

            owasp = meta.get("owasp", [])
            if isinstance(owasp, str):
                owasp = [owasp]

            rule_id = item.get("check_id", "")
            
            finding = {
                "rule_id":      rule_id,
                "rule_name":    rule_id.split(".")[-1],
                "severity":     extra.get("severity", "INFO"),
                "category":     meta.get("category", ""),
                "message":      extra.get("message", ""),
                "filepath":     _make_relative(item.get("path", ""), target_path_obj),
                "line_start":   item.get("start", {}).get("line", 0),
                "line_end":     item.get("end", {}).get("line", 0),
                "code_snippet": extra.get("lines", "").strip(),
                "cwe":          cwe,
                "owasp":        owasp,
                "fix":          extra.get("fix", ""),
                "confidence":   meta.get("confidence", ""),
            }
            findings_list.append(finding)
        except Exception as exc:
            logger.debug(f"Skipping malformed finding: {exc}")

    # STEP 6 — Deduplicate
    seen: set[tuple] = set()
    deduped_findings: list[dict] = []
    for f in findings_list:
        key = (f["rule_id"], f["filepath"], f["line_start"])
        if key not in seen:
            seen.add(key)
            deduped_findings.append(f)

    # STEP 8 — Severity summary (count from FULL deduplicated list)
    summary = {"ERROR": 0, "WARNING": 0, "INFO": 0}
    for f in deduped_findings:
        sev = f["severity"].upper()
        summary[sev] = summary.get(sev, 0) + 1

    # STEP 7 — Cap at max_findings
    total_before_cap = len(deduped_findings)
    capped_findings = deduped_findings[:max_findings]

    # STEP 9 — Semgrep errors
    semgrep_errors = []
    for err in data.get("errors", []):
        semgrep_errors.append({
            "code":    err.get("code", 0),
            "level":   err.get("level", ""),
            "message": str(err.get("message", ""))[:200],
        })

    # STEP 10 — Stats
    semgrep_stats = data.get("stats", {}).get("total", {})
    stats = {
        "total_findings":    total_before_cap,
        "returned_findings": len(capped_findings),
        "files_scanned":     semgrep_stats.get("files", 0),
        "rules_run":         semgrep_stats.get("rules", 0),
        "scan_time_seconds": float(semgrep_stats.get("time", 0.0)),
    }
    
    logger.info(
        f"semgrep complete: {total_before_cap} raw findings, "
        f"{len(capped_findings)} returned — "
        f"E:{summary['ERROR']} W:{summary['WARNING']} I:{summary['INFO']}"
    )

    return {
        "tool": "semgrep",
        "target": target_str,
        "rules_used": rules,
        "semgrep_available": True,
        "run_error": None,
        "findings": capped_findings,
        "severity_summary": summary,
        "semgrep_errors": semgrep_errors,
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(levelname)s  %(name)s  %(message)s"
    )

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    result = run_semgrep(target_path=target, rules="auto")
    print(json.dumps(result, indent=2))

    s = result["severity_summary"]
    print(
        f"\nFound {result['stats']['total_findings']} findings: "
        f"{s['ERROR']} errors, {s['WARNING']} warnings, {s['INFO']} info"
    )
    if result["run_error"]:
        print(f"Run error: {result['run_error']}")
