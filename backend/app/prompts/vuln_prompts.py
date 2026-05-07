import json
from typing import Any


SYSTEM_PROMPT = """
You are a senior application security engineer performing static analysis.
Return a concise, accurate vulnerability report strictly in JSON.
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
Analyze the findings below and produce a structured vulnerability report.

=== SEMGREP FINDINGS ({len(semgrep_findings)}) ===
{json.dumps(semgrep_findings, indent=2)}

=== AST SECURITY FLAGS (with source code) ===
{json.dumps(flagged_files, indent=2, default=str)}

=== CALL GRAPH HOTSPOTS ===
{json.dumps(call_graph.get("hotspots", []), indent=2)}

=== CIRCULAR IMPORTS ===
{json.dumps(call_graph.get("circular_imports", []), indent=2)}

For each finding provide:
1. severity: CRITICAL / HIGH / MEDIUM / LOW
2. title: short descriptive title
3. description: what the vulnerability is
4. filepath + line_start
5. code_snippet: the vulnerable code
6. exploitability: is it actually exploitable given the call graph context?
7. confidence: HIGH / MEDIUM / LOW -- with a brief reason
   (e.g. "HIGH -- confirmed by Semgrep rule match",
	   "MEDIUM -- pattern detected but requires manual review",
	   "LOW -- flagged by heuristic, may be false positive")
8. fix: specific code fix recommendation
9. cwe: relevant CWE ID if applicable

Return ONLY a valid JSON object with this exact schema (no markdown fences):
{{
  "findings": [
	{{
	  "severity":       "CRITICAL",
	  "title":          "SQL Injection via string concatenation",
	  "description":    "...",
	  "filepath":       "src/auth.py",
	  "line_start":     42,
	  "code_snippet":   "cursor.execute('SELECT * FROM users WHERE id=' + user_id)",
	"exploitability": "HIGH -- fetch_user() is called directly from the public API",
	"confidence":     "HIGH -- confirmed by Semgrep rule match and AST flag",
	  "fix":            "Use parameterized queries: cursor.execute(..., (user_id,))",
	  "cwe":            "CWE-89"
	}}
  ],
  "summary": "Found 3 critical, 2 high, 1 medium vulnerability",
  "risk_score": 8.5,
  "most_vulnerable_file": "src/auth.py"
}}
""".strip()

	return [
		{"role": "system", "content": SYSTEM_PROMPT},
		{"role": "user", "content": user_prompt},
	]
