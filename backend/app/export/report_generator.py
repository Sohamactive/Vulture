import base64
import html
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Iterable
from zipfile import ZIP_DEFLATED, ZipFile

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def generate_report(report: dict[str, Any], export_format: str) -> dict[str, Any]:
    normalized_format = (export_format or "json").lower()

    if normalized_format == "docx":
        content = _build_docx_bytes(report)
        encoded = base64.b64encode(content).decode("ascii")
        scan_id = str(report.get("id") or "report")
        return {
            "format": "docx",
            "filename": f"vulture-report-{scan_id}.docx",
            "mime_type": DOCX_MIME_TYPE,
            "content_base64": encoded,
        }

    return {"format": normalized_format, "report": report}


def _build_docx_bytes(report: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", _content_types_xml())
        docx.writestr("_rels/.rels", _package_rels_xml())
        docx.writestr("docProps/core.xml", _core_props_xml())
        docx.writestr("docProps/app.xml", _app_props_xml())
        docx.writestr("word/_rels/document.xml.rels", _document_rels_xml())
        docx.writestr("word/styles.xml", _styles_xml())
        docx.writestr("word/document.xml", _document_xml(report))
    return buffer.getvalue()


def _xml(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=False)


def _safe_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        if digits:
            return int(digits)
    return 0


def _safe_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return 0.0
    return 0.0


def _summary_count(summary: dict[str, Any], key: str) -> int:
    return _safe_int(summary.get(key, 0))


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_issues(report: dict[str, Any]) -> list[dict[str, Any]]:
    issues = report.get("issues") or []
    normalized: list[dict[str, Any]] = []
    if not isinstance(issues, list):
        return normalized
    for issue in issues:
        if isinstance(issue, dict):
            normalized.append(issue)
    return normalized


def _duration_text(ms: int) -> str:
    if ms <= 0:
        return "N/A"
    total_seconds = ms / 1000
    if total_seconds < 60:
        return f"{total_seconds:.1f}s"
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}m {seconds}s"


def _p(
    text: Any,
    *,
    style: str | None = None,
    bold: bool = False,
    preserve_space: bool = False,
    mono: bool = False,
    color: str | None = None,
    spacing_before: int | None = None,
    spacing_after: int | None = None,
) -> str:
    ppr_parts: list[str] = []
    if style:
        ppr_parts.append(f'<w:pStyle w:val="{style}"/>')
    if spacing_before is not None or spacing_after is not None:
        before = f' w:before="{spacing_before}"' if spacing_before is not None else ""
        after = f' w:after="{spacing_after}"' if spacing_after is not None else ""
        ppr_parts.append(f"<w:spacing{before}{after}/>")
    ppr = f"<w:pPr>{''.join(ppr_parts)}</w:pPr>" if ppr_parts else ""

    run_props: list[str] = []
    if bold:
        run_props.append("<w:b/>")
    if mono:
        run_props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>')
    if color:
        run_props.append(f'<w:color w:val="{color}"/>')
    rpr = f"<w:rPr>{''.join(run_props)}</w:rPr>" if run_props else ""

    space_attr = ' xml:space="preserve"' if preserve_space else ""
    return f"<w:p>{ppr}<w:r>{rpr}<w:t{space_attr}>{_xml(text)}</w:t></w:r></w:p>"


def _code_block(code: Any) -> str:
    if not code:
        return _p("No snippet provided.", style="Code")
    lines = str(code).replace("\r\n", "\n").split("\n")
    if not lines:
        return _p("No snippet provided.", style="Code")
    parts = []
    for line in lines:
        parts.append(_p(line if line else " ", style="Code", preserve_space=True, mono=True))
    return "".join(parts)


def _severity_style(severity: str) -> str:
    sev = str(severity or "").lower()
    if sev == "critical":
        return "BannerCritical"
    if sev == "high":
        return "BannerHigh"
    if sev == "medium":
        return "BannerMedium"
    return "BannerLow"


def _table(rows: list[list[str]], headers: list[str] | None = None, col_widths: list[int] | None = None) -> str:
    if not rows and not headers:
        return ""

    column_count = len(headers) if headers else len(rows[0])
    widths = col_widths or [int(9600 / max(1, column_count)) for _ in range(column_count)]
    if len(widths) < column_count:
        widths = widths + [widths[-1] for _ in range(column_count - len(widths))]

    table_rows: list[str] = []
    if headers:
        cells = []
        for idx, header in enumerate(headers):
            cells.append(
                "<w:tc>"
                f"<w:tcPr><w:tcW w:w=\"{widths[idx]}\" w:type=\"dxa\"/></w:tcPr>"
                f"{_p(header, bold=True)}"
                "</w:tc>"
            )
        table_rows.append("<w:tr>" + "".join(cells) + "</w:tr>")

    for row in rows:
        cells = []
        for idx in range(column_count):
            value = row[idx] if idx < len(row) else ""
            cells.append(
                "<w:tc>"
                f"<w:tcPr><w:tcW w:w=\"{widths[idx]}\" w:type=\"dxa\"/></w:tcPr>"
                f"{_p(value)}"
                "</w:tc>"
            )
        table_rows.append("<w:tr>" + "".join(cells) + "</w:tr>")

    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths[:column_count])
    return (
        "<w:tbl>"
        "<w:tblPr>"
        '<w:tblStyle w:val="TableGrid"/>'
        '<w:tblW w:w="9600" w:type="dxa"/>'
        "</w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid>"
        f"{''.join(table_rows)}"
        "</w:tbl>"
    )


def _list(items: Iterable[str]) -> str:
    parts: list[str] = []
    for item in items:
        parts.append(_p(f"- {item}", style="ListParagraph"))
    return "".join(parts)


def _line_range(issue: dict[str, Any]) -> str:
    line_numbers = issue.get("line_numbers")
    if isinstance(line_numbers, list) and line_numbers:
        return ", ".join(str(_safe_int(x)) for x in line_numbers if _safe_int(x) > 0)
    line_start = _safe_int(issue.get("line_start"))
    line_end = _safe_int(issue.get("line_end"))
    if line_start <= 0:
        return "N/A"
    if line_end > 0 and line_end >= line_start:
        return f"{line_start}-{line_end}"
    return str(line_start)


def _chain_text(chain: Any) -> str:
    items = _as_str_list(chain)
    if not items:
        return "N/A"
    return " -> ".join(items)


def _document_xml(report: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = _as_dict(report.get("summary"))
    issues = _normalize_issues(report)
    score = _safe_int(report.get("security_score"))
    scanned_files = _safe_int(report.get("scanned_files"))
    scan_duration_ms = _safe_int(report.get("scan_duration_ms"))
    total_findings = sum(_summary_count(summary, key) for key in SEVERITY_ORDER)

    executive = _as_dict(summary.get("executive_risk_verdict"))
    ai_assessment = _as_dict(summary.get("ai_security_assessment"))
    score_breakdown = _as_dict(summary.get("security_score_breakdown"))
    repository_intel = _as_dict(summary.get("repository_intelligence"))
    attack_surface = _as_dict(summary.get("attack_surface_overview"))
    heatmap = _as_list(summary.get("file_risk_heatmap"))
    attack_scenarios = _as_str_list(summary.get("attack_scenarios"))
    reachability = _as_dict(summary.get("reachability_analysis"))
    exploit_chains = _as_list(summary.get("exploit_chains"))
    privacy = _as_dict(summary.get("privacy_processing"))
    risk_prioritization = _as_list(summary.get("risk_prioritization"))
    dedup = _as_list(summary.get("finding_deduplication"))

    parts: list[str] = [
        _p("Vulture Security Scan Report", style="Title"),
        _p(f"Generated on {now}", style="Subtitle"),
        _p("Executive Summary", style="Heading1"),
        _table(
            [
                ["Scan ID", str(report.get("id") or "N/A")],
                ["Security Score", f"{score}/100"],
                ["Total Findings", str(total_findings)],
                ["Scanned Files", str(scanned_files)],
                ["Scan Duration", _duration_text(scan_duration_ms)],
            ],
            col_widths=[2800, 6800],
        ),
        _p("Severity Breakdown", style="Heading2"),
        _table(
            [[severity.title(), str(_summary_count(summary, severity))] for severity in SEVERITY_ORDER],
            headers=["Severity", "Count"],
            col_widths=[3000, 6600],
        ),
    ]

    parts.extend(
        [
            _p("Executive Risk Verdict", style="Heading1"),
            _table(
                [
                    ["Overall risk posture", str(executive.get("overall_risk_posture") or "N/A")],
                    ["Most critical risk area", str(executive.get("most_critical_risk_area") or "N/A")],
                    [
                        "Remotely exploitable findings",
                        str(executive.get("remotely_exploitable_findings") or "N/A"),
                    ],
                ],
                col_widths=[3600, 6000],
            ),
            _p("AI Security Assessment", style="Heading1"),
            _p(str(ai_assessment.get("repository_wide_summary") or "No AI assessment provided."), style="BodyText"),
            _p("Top Risk Categories", style="Heading3"),
            _list(_as_str_list(ai_assessment.get("top_risk_categories")) or ["N/A"]),
            _p("Likely Attack Vectors", style="Heading3"),
            _list(_as_str_list(ai_assessment.get("likely_attack_vectors")) or ["N/A"]),
            _p("Architectural Weaknesses", style="Heading3"),
            _list(_as_str_list(ai_assessment.get("architectural_weaknesses")) or ["N/A"]),
        ]
    )

    parts.append(_p("Security Score Breakdown", style="Heading1"))
    breakdown_rows: list[list[str]] = []
    for category in (
        "Authentication Security",
        "Input Validation",
        "Dependency Security",
        "Transport Security",
        "Configuration Security",
        "Secrets Management",
    ):
        entry = _as_dict(score_breakdown.get(category))
        breakdown_rows.append(
            [
                category,
                f"{_safe_int(entry.get('score'))}/100",
                str(entry.get("explanation") or "N/A"),
            ]
        )
    parts.append(
        _table(
            breakdown_rows,
            headers=["Category", "Score", "Explanation"],
            col_widths=[2600, 1600, 5400],
        )
    )

    parts.extend(
        [
            _p("Repository Intelligence", style="Heading1"),
            _table(
                [
                    ["Files analyzed", str(_safe_int(repository_intel.get("files_analyzed")))],
                    ["Parsed files", str(_safe_int(repository_intel.get("parsed_files")))],
                    ["Symbols indexed", str(_safe_int(repository_intel.get("symbols_indexed")))],
                    ["Call edges", str(_safe_int(repository_intel.get("call_edges")))],
                    [
                        "Resolution rate",
                        f"{_safe_float(repository_intel.get('resolution_rate')) * 100:.1f}%",
                    ],
                    [
                        "Circular imports",
                        str(len(_as_list(repository_intel.get("circular_imports")))),
                    ],
                    [
                        "Unresolved call groups",
                        str(len(_as_list(repository_intel.get("unresolved_calls")))),
                    ],
                ],
                col_widths=[3200, 6400],
            ),
            _p("Hotspots", style="Heading3"),
            _list(_as_str_list(repository_intel.get("hotspots")) or ["N/A"]),
            _p("Attack Surface Overview", style="Heading1"),
            _table(
                [
                    ["API routes", str(len(_as_list(attack_surface.get("api_routes"))))],
                    ["Auth endpoints", str(len(_as_list(attack_surface.get("auth_endpoints"))))],
                    ["Websocket endpoints", str(len(_as_list(attack_surface.get("websocket_endpoints"))))],
                    ["File upload handlers", str(len(_as_list(attack_surface.get("file_upload_handlers"))))],
                    ["External requests", str(len(_as_list(attack_surface.get("external_requests"))))],
                    ["Database connectors", str(len(_as_list(attack_surface.get("database_connectors"))))],
                    ["Filesystem access points", str(len(_as_list(attack_surface.get("filesystem_access_points"))))],
                ],
                col_widths=[3600, 6000],
            ),
        ]
    )

    parts.append(_p("File Risk Heatmap", style="Heading1"))
    heatmap_rows: list[list[str]] = []
    for item in heatmap[:12]:
        if not isinstance(item, dict):
            continue
        heatmap_rows.append(
            [
                str(item.get("filepath") or "N/A"),
                str(_safe_int(item.get("vulnerability_count"))),
                str(item.get("dominant_risk_type") or "N/A"),
                str(item.get("highest_severity") or "N/A"),
            ]
        )
    if heatmap_rows:
        parts.append(
            _table(
                heatmap_rows,
                headers=["File", "Count", "Dominant Risk", "Highest Severity"],
                col_widths=[4200, 1000, 2600, 1800],
            )
        )
    else:
        parts.append(_p("No file-level heatmap data available.", style="BodyText"))

    parts.extend(
        [
            _p("Attack Scenarios", style="Heading1"),
            _list(attack_scenarios or ["N/A"]),
            _p("Reachability Analysis", style="Heading1"),
        ]
    )
    reach_counts = _as_dict(reachability.get("counts"))
    parts.append(
        _table(
            [[k.title(), str(_safe_int(v))] for k, v in reach_counts.items()],
            headers=["Reachability", "Findings"],
            col_widths=[4200, 5400],
        )
        if reach_counts
        else _p("No reachability data available.", style="BodyText")
    )

    parts.append(_p("Exploit Chains", style="Heading1"))
    if exploit_chains:
        for chain in exploit_chains[:10]:
            parts.append(_p(_chain_text(chain), style="ListParagraph"))
    else:
        parts.append(_p("No chained exploit paths identified.", style="BodyText"))

    parts.append(_p("Finding Deduplication", style="Heading1"))
    dedup_rows: list[list[str]] = []
    for group in dedup[:20]:
        if not isinstance(group, dict):
            continue
        dedup_rows.append(
            [
                str(group.get("group") or "N/A"),
                str(group.get("title") or "N/A"),
                str(_safe_int(group.get("instances"))),
            ]
        )
    if dedup_rows:
        parts.append(_table(dedup_rows, headers=["Group", "Title", "Instances"], col_widths=[1400, 6400, 1800]))
    else:
        parts.append(_p("No repeated findings grouped.", style="BodyText"))

    parts.append(_p("Risk Prioritization", style="Heading1"))
    prio_rows: list[list[str]] = []
    for item in risk_prioritization[:12]:
        if not isinstance(item, dict):
            continue
        prio_rows.append(
            [
                str(item.get("remediation_priority") or "N/A"),
                str(item.get("severity") or "N/A"),
                str(item.get("reachability") or "N/A"),
                str(item.get("title") or "N/A"),
                str(_safe_int(item.get("priority_score"))),
            ]
        )
    if prio_rows:
        parts.append(
            _table(
                prio_rows,
                headers=["Priority", "Severity", "Reachability", "Finding", "Score"],
                col_widths=[1700, 1200, 2000, 3700, 1000],
            )
        )
    else:
        parts.append(_p("No prioritization data available.", style="BodyText"))

    parts.extend(
        [
            _p("Privacy and Processing", style="Heading1"),
            _list(
                [
                    "Local parsing occurs before AI inference.",
                    "Static analysis (AST, Tree-sitter, Semgrep, call graph) runs locally.",
                    "AWS Bedrock is used for inference enrichment.",
                    str(
                        privacy.get("bedrock_training_policy")
                        or "Bedrock does not use customer data for model training."
                    ),
                ]
            ),
            _p("Findings", style="Heading1"),
        ]
    )

    if not issues:
        parts.append(_p("No vulnerabilities were found in this scan.", style="BodyText"))
    else:
        for index, issue in enumerate(issues, start=1):
            severity = str(issue.get("severity") or "low").lower()
            remediation = issue.get("remediation") or []
            if isinstance(remediation, str):
                remediation = [remediation]
            if not isinstance(remediation, list):
                remediation = []

            parts.extend(
                [
                    _p(f"{index}. {issue.get('title') or 'Untitled finding'}", style="Heading2"),
                    _p(
                        f"{severity.upper()} FINDING",
                        style=_severity_style(severity),
                        bold=True,
                        color="FFFFFF",
                    ),
                    _table(
                        [
                            ["Severity", severity.upper()],
                            ["Confidence Score", f"{_safe_int(issue.get('confidence_score'))}/100"],
                            ["Exploitability", str(issue.get("exploitability") or "N/A")],
                            ["Business Impact", str(issue.get("business_impact") or "N/A")],
                            ["False Positive Risk", str(issue.get("false_positive_risk") or "N/A")],
                            ["Reachability", str(issue.get("reachability") or "N/A")],
                            ["OWASP", str(issue.get("owasp_category") or "N/A")],
                            ["CWE", str(issue.get("cwe_id") or "N/A")],
                            ["File", str(issue.get("file_path") or issue.get("filepath") or "N/A")],
                            ["Line(s)", _line_range(issue)],
                            ["Remediation Priority", str(issue.get("remediation_priority") or "N/A")],
                        ],
                        col_widths=[3200, 6400],
                    ),
                    _p("Description", style="Heading3"),
                    _p(issue.get("description") or "No description provided.", style="BodyText"),
                    _p("Attack Scenario", style="Heading3"),
                    _p(issue.get("attack_scenario") or "No attack scenario provided.", style="BodyText"),
                    _p("Exploit Chain", style="Heading3"),
                    _p(_chain_text(issue.get("exploit_chain")), style="BodyText"),
                    _p("Code Snippet", style="Heading3"),
                    _code_block(issue.get("code_snippet")),
                    _p("Recommended Remediation", style="Heading3"),
                ]
            )

            if remediation:
                parts.extend([_p(f"- {step}", style="ListParagraph") for step in remediation])
            else:
                parts.append(_p("No remediation guidance provided.", style="BodyText"))

    body = "".join(parts) + (
        "<w:sectPr>"
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080" w:header="708" w:footer="708" w:gutter="0"/>'
        "<w:cols w:space=\"708\"/>"
        "<w:docGrid w:linePitch=\"360\"/>"
        "</w:sectPr>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )


def _package_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _core_props_xml() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Vulture Security Scan Report</dc:title>"
        "<dc:creator>Vulture</dc:creator>"
        "<cp:lastModifiedBy>Vulture</cp:lastModifiedBy>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _document_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _app_props_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>Vulture</Application>"
        "</Properties>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/>'
        '<w:rPr><w:sz w:val="22"/></w:rPr>'
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Title">'
        '<w:name w:val="Title"/>'
        "<w:pPr><w:jc w:val=\"center\"/><w:spacing w:after=\"300\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"40\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Subtitle">'
        '<w:name w:val="Subtitle"/>'
        "<w:pPr><w:jc w:val=\"center\"/><w:spacing w:after=\"360\"/></w:pPr>"
        '<w:rPr><w:color w:val="666666"/><w:sz w:val="20"/></w:rPr>'
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/>'
        "<w:pPr><w:spacing w:before=\"300\" w:after=\"160\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"30\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/>'
        "<w:pPr><w:spacing w:before=\"240\" w:after=\"110\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"26\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Heading3">'
        '<w:name w:val="heading 3"/>'
        "<w:pPr><w:spacing w:before=\"180\" w:after=\"80\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"23\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="BodyText">'
        '<w:name w:val="Body Text"/>'
        "<w:pPr><w:spacing w:after=\"80\"/></w:pPr>"
        "<w:rPr><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Code">'
        '<w:name w:val="Code"/>'
        "<w:pPr><w:spacing w:before=\"0\" w:after=\"0\"/><w:ind w:left=\"240\"/>"
        '<w:shd w:val="clear" w:color="auto" w:fill="111827"/>'
        "</w:pPr>"
        '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/><w:color w:val="FFFFFF"/><w:sz w:val="19"/></w:rPr>'
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="ListParagraph">'
        '<w:name w:val="List Paragraph"/>'
        "<w:pPr><w:ind w:left=\"360\"/><w:spacing w:after=\"60\"/></w:pPr>"
        "<w:rPr><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="BannerCritical">'
        '<w:name w:val="Banner Critical"/>'
        "<w:pPr><w:spacing w:before=\"100\" w:after=\"80\"/><w:ind w:left=\"120\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"9F1239\"/></w:pPr>"
        "<w:rPr><w:b/><w:color w:val=\"FFFFFF\"/><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="BannerHigh">'
        '<w:name w:val="Banner High"/>'
        "<w:pPr><w:spacing w:before=\"100\" w:after=\"80\"/><w:ind w:left=\"120\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"B45309\"/></w:pPr>"
        "<w:rPr><w:b/><w:color w:val=\"FFFFFF\"/><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="BannerMedium">'
        '<w:name w:val="Banner Medium"/>'
        "<w:pPr><w:spacing w:before=\"100\" w:after=\"80\"/><w:ind w:left=\"120\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"A16207\"/></w:pPr>"
        "<w:rPr><w:b/><w:color w:val=\"FFFFFF\"/><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="BannerLow">'
        '<w:name w:val="Banner Low"/>'
        "<w:pPr><w:spacing w:before=\"100\" w:after=\"80\"/><w:ind w:left=\"120\"/><w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"1E3A8A\"/></w:pPr>"
        "<w:rPr><w:b/><w:color w:val=\"FFFFFF\"/><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        "</w:styles>"
    )
