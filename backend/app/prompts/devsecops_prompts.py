import json
from typing import Any, List

SYSTEM_PROMPT = """
You are a DevSecOps engineer advising a product team.
Use ONLY the report data provided. If something is unknown, say so.
If the user question is not about the current scan report or security, respond with:
"Out of scope: I can only answer questions about the current scan report and security findings."

Response requirements:
- Start with "Do:" followed by 3-6 bullets.
- Then "Do not:" followed by 2-4 bullets.
- Then "Prioritized next steps:" followed by 3-5 bullets.
- Keep it concise and practical.
- Plain text only; no markdown fences.
""".strip()


def _format_history(history: List[dict], max_items: int = 6) -> str:
    trimmed = history[-max_items:] if history else []
    if not trimmed:
        return "None"
    lines = [
        f"{item.get('role', 'user')}: {item.get('content', '')}" for item in trimmed]
    return "\n".join(lines)


def build_devsecops_messages(
    report_context: dict,
    history: List[dict],
    user_message: str,
) -> List[dict]:
    issues = report_context.get("issues", [])
    trimmed_issues = issues[:10]

    user_prompt = (
        "You are answering a security question about the current scan report.\n\n"
        f"User question: {user_message}\n\n"
        "Report context:\n"
        f"{json.dumps({
            'scan_id': report_context.get('scan_id'),
            'repo': report_context.get('repo'),
            'branch': report_context.get('branch'),
            'security_score': report_context.get('security_score'),
            'summary': report_context.get('summary', {}),
            'issues': trimmed_issues,
        }, indent=2)}\n\n"
        "Recent chat history:\n"
        f"{_format_history(history)}"
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
