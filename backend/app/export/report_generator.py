from typing import Any, Dict


def generate_report(report: Dict[str, Any], export_format: str) -> Dict[str, Any]:
    return {"format": export_format, "report": report}
