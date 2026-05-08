import json
from typing import Any


SYSTEM_PROMPT = """
You are a senior application security engineer performing static analysis.
Return concise, accurate contextual intelligence strictly in JSON.
Do not generate full report formatting or narrative sections.
Only enrich findings and repository context.
Do not include markdown fences, commentary, or extra keys.
""".strip()


def _extract_function_snippets(
	source: str,
	functions: list[dict],
	max_functions: int = 5,
	max_lines_per_fn: int = 40,
) -> list[dict]:
	"""Extract actual source code for top functions in a file.

	Returns a list of {name, line_start, line_end, args, body} dicts.
	Truncates long function bodies to keep the prompt under control.
	"""
	lines = source.splitlines()
	snippets: list[dict] = []
	for fn in functions[:max_functions]:
		start = fn.get("line_start", 1) - 1
		end = fn.get("line_end") or (start + max_lines_per_fn)
		body_lines = lines[start:end]
		if len(body_lines) > max_lines_per_fn:
			body_lines = body_lines[:max_lines_per_fn] + ["    # ... truncated ..."]
		snippets.append({
			"name": fn.get("name", "?"),
			"line_start": fn.get("line_start"),
			"line_end": fn.get("line_end"),
			"args": fn.get("args", []),
			"body": "\n".join(body_lines),
		})
	return snippets


def _build_flagged_files(parse_results: list[dict], source_files: dict[str, str]) -> list[dict]:
	flagged_files: list[dict] = []
	for pr in parse_results:
		flags = pr.get("security_flags", {})
		active = [key for key, value in flags.items() if value]
		if not active:
			continue

		filepath = pr.get("filepath")
		entry: dict[str, Any] = {
			"filepath": filepath,
			"flags": active,
		}

		source = source_files.get(filepath, "") if filepath else ""
		if source and pr.get("functions"):
			entry["functions"] = _extract_function_snippets(source, pr["functions"])
		else:
			entry["functions"] = [
				{
					"name": fn.get("name"),
					"args": fn.get("args", []),
					"line_start": fn.get("line_start"),
				}
				for fn in pr.get("functions", [])[:5]
			]

		flagged_files.append(entry)

	return flagged_files


def build_vuln_agent_messages(state: dict) -> list[dict]:
	semgrep_findings = state.get("semgrep_out", {}).get("findings", [])
	parse_results = state.get("parse_results", [])
	call_graph = state.get("call_graph_out", {})
	source_files = state.get("file_reader_out", {}).get("files", {})

	flagged_files = _build_flagged_files(parse_results, source_files)

	user_prompt = f"""
Analyze static-analysis evidence below.
Task: enrich findings context only; renderer will build final report deterministically.

=== SEMGREP FINDINGS ({len(semgrep_findings)}) ===
{json.dumps(semgrep_findings, indent=2)}

=== AST SECURITY FLAGS (with source code) ===
{json.dumps(flagged_files, indent=2, default=str)}

=== CALL GRAPH HOTSPOTS ===
{json.dumps(call_graph.get("hotspots", []), indent=2)}

=== CIRCULAR IMPORTS ===
{json.dumps(call_graph.get("circular_imports", []), indent=2)}

For each finding provide these fields:
1. severity: CRITICAL / HIGH / MEDIUM / LOW
2. title
3. description
4. filepath
5. line_start
6. line_end (optional)
7. code_snippet
8. exploitability (LOW/MEDIUM/HIGH/CRITICAL + short reason)
9. business_impact (short)
10. false_positive_risk (LOW/MEDIUM/HIGH + short reason)
11. attack_scenario (1-2 sentence attacker workflow)
12. exploit_chain (ordered list; empty if none)
13. remediation_priority (P0/P1/P2/P3 + short reason)
14. reachability (publicly reachable/auth-protected/internal only/not externally exposed)
15. fix
16. cwe
17. owasp_category: one of
   "A01:Access Control", "A02:Crypto", "A03:Injection", "A04:Design",
   "A05:Config", "A06:Outdated", "A07:Auth", "A08:Integrity",
   "A09:Logging", "A10:SSRF"
18. confidence_score (0-100; evidence-based, not random)

IMPORTANT:
- Keep output deterministic and concise.
- Every finding MUST include exact filepath from input when available.
- If uncertain, use filepath where Semgrep/AST flag detected.
- Do not merge multiple files into one finding unless they are exact duplicates.
- Do not fabricate endpoints, files, symbols, or package names absent from evidence.
- Provide repository-level assessments as concise bullets/phrases, not long prose.

Return ONLY a valid JSON object with this schema (no markdown fences):
{{
  "findings": [
	{{
	  "severity":       "CRITICAL",
	  "title":          "SQL Injection via string concatenation",
	  "description":    "...",
	  "filepath":       "src/auth.py",
	  "line_start":     42,
      "line_end":       42,
	  "code_snippet":   "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
	  "exploitability": "HIGH -- reachable from public endpoint",
      "business_impact": "Unauthorized data read/write",
      "false_positive_risk": "LOW -- strong rule + contextual evidence",
      "attack_scenario": "Attacker sends crafted id parameter to bypass query safety and dump user records.",
      "exploit_chain": ["SQL injection", "database dump"],
      "remediation_priority": "P0 -- externally reachable and high impact",
      "reachability": "publicly reachable",
	  "fix":            "Use parameterized queries: cursor.execute(..., (user_id,))",
	  "cwe":            "CWE-89",
	  "owasp_category": "A03:Injection",
      "confidence_score": 95
	}}
  ],
  "summary": "Concise repository-wide risk summary",
  "executive_risk_verdict": {{
    "overall_risk_posture": "High",
    "most_critical_risk_area": "Authentication and access control",
    "remotely_exploitable_findings": "Likely yes"
  }},
  "ai_security_assessment": {{
    "repository_wide_summary": "Short summary",
    "top_risk_categories": ["A07:Auth", "A03:Injection"],
    "likely_attack_vectors": ["Auth bypass", "Injection via API inputs"],
    "architectural_weaknesses": ["Over-trusted internal calls", "Weak boundary validation"]
  }},
  "attack_scenarios": [
    "Attacker forges JWT token due to weak verification and reaches admin route."
  ],
  "risk_score": 8.5,
  "most_vulnerable_file": "src/auth.py"
}}
""".strip()

	return [
		{"role": "system", "content": SYSTEM_PROMPT},
		{"role": "user", "content": user_prompt},
	]
