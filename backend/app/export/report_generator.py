import base64
import html
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Iterable
from zipfile import ZIP_DEFLATED, ZipFile

DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


def generate_report(report: Dict[str, Any], export_format: str) -> Dict[str, Any]:
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


def _build_docx_bytes(report: Dict[str, Any]) -> bytes:
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


def _summary_count(summary: Dict[str, Any], key: str) -> int:
    return _safe_int(summary.get(key, 0))


def _normalize_issues(report: Dict[str, Any]) -> list[Dict[str, Any]]:
    issues = report.get("issues") or []
    normalized: list[Dict[str, Any]] = []
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
        run_props.append(
            '<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
        )
    rpr = f"<w:rPr>{''.join(run_props)}</w:rPr>" if run_props else ""

    space_attr = ' xml:space="preserve"' if preserve_space else ""
    return f"<w:p>{ppr}<w:r>{rpr}<w:t{space_attr}>{_xml(text)}</w:t></w:r></w:p>"


def _code_block(code: Any) -> str:
    if not code:
        return _p("No snippet provided.", style="Code")
    lines = str(code).replace("\r\n", "\n").split("\n")
    parts = []
    for line in lines:
        parts.append(_p(line if line else " ", style="Code", preserve_space=True, mono=True))
    return "".join(parts)


def _table(rows: Iterable[tuple[str, str]]) -> str:
    row_xml = []
    for label, value in rows:
        row_xml.append(
            "<w:tr>"
            "<w:tc>"
            "<w:tcPr><w:tcW w:w=\"2800\" w:type=\"dxa\"/></w:tcPr>"
            f"{_p(label, bold=True)}"
            "</w:tc>"
            "<w:tc>"
            "<w:tcPr><w:tcW w:w=\"6800\" w:type=\"dxa\"/></w:tcPr>"
            f"{_p(value)}"
            "</w:tc>"
            "</w:tr>"
        )
    return (
        "<w:tbl>"
        "<w:tblPr>"
        "<w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"9600\" w:type=\"dxa\"/>"
        "</w:tblPr>"
        "<w:tblGrid><w:gridCol w:w=\"2800\"/><w:gridCol w:w=\"6800\"/></w:tblGrid>"
        f"{''.join(row_xml)}"
        "</w:tbl>"
    )


def _document_xml(report: Dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    issues = _normalize_issues(report)
    score = _safe_int(report.get("security_score"))
    scanned_files = _safe_int(report.get("scanned_files"))
    scan_duration_ms = _safe_int(report.get("scan_duration_ms"))
    total_findings = sum(_summary_count(summary, key) for key in SEVERITY_ORDER)

    parts: list[str] = [
        _p("Vulture Security Scan Report", style="Title"),
        _p(f"Generated on {now}", style="Subtitle"),
        _p("Executive Summary", style="Heading1"),
        _table(
            (
                ("Scan ID", str(report.get("id") or "N/A")),
                ("Security Score", f"{score}/100"),
                ("Total Findings", str(total_findings)),
                ("Scanned Files", str(scanned_files)),
                ("Scan Duration", _duration_text(scan_duration_ms)),
            )
        ),
        _p("Severity Breakdown", style="Heading2"),
        _table(
            tuple(
                (severity.title(), str(_summary_count(summary, severity)))
                for severity in SEVERITY_ORDER
            )
        ),
        _p("Findings", style="Heading1"),
    ]

    if not issues:
        parts.append(_p("No vulnerabilities were found in this scan.", style="BodyText"))
    else:
        for index, issue in enumerate(issues, start=1):
            remediation = issue.get("remediation") or []
            if isinstance(remediation, str):
                remediation = [remediation]
            if not isinstance(remediation, list):
                remediation = []

            parts.extend(
                [
                    _p(f"{index}. {issue.get('title') or 'Untitled finding'}", style="Heading2"),
                    _table(
                        (
                            ("Severity", str(issue.get("severity") or "unknown").upper()),
                            ("Source", str(issue.get("detection_source") or "N/A")),
                            ("OWASP", str(issue.get("owasp_category") or "N/A")),
                            ("CWE", str(issue.get("cwe_id") or "N/A")),
                            ("File", str(issue.get("file_path") or "N/A")),
                            (
                                "Line",
                                str(issue.get("line_start") or "N/A")
                                if not issue.get("line_end")
                                else f"{issue.get('line_start') or 'N/A'} - {issue.get('line_end')}",
                            ),
                        )
                    ),
                    _p("Description", style="Heading3"),
                    _p(issue.get("description") or "No description provided.", style="BodyText"),
                    _p("Code Snippet", style="Heading3"),
                    _code_block(issue.get("code_snippet")),
                    _p("Recommended Remediation", style="Heading3"),
                ]
            )

            if remediation:
                for step in remediation:
                    parts.append(_p(f"- {step}", style="ListParagraph"))
            else:
                parts.append(_p("No remediation guidance provided.", style="BodyText"))

    body = "".join(parts) + (
        "<w:sectPr>"
        '<w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>'
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
        "<w:pPr><w:jc w:val=\"center\"/><w:spacing w:after=\"280\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"40\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Subtitle">'
        '<w:name w:val="Subtitle"/>'
        "<w:pPr><w:jc w:val=\"center\"/><w:spacing w:after=\"320\"/></w:pPr>"
        '<w:rPr><w:color w:val="666666"/><w:sz w:val="20"/></w:rPr>'
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/>'
        "<w:pPr><w:spacing w:before=\"280\" w:after=\"160\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"30\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/>'
        "<w:pPr><w:spacing w:before=\"240\" w:after=\"120\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"26\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Heading3">'
        '<w:name w:val="heading 3"/>'
        "<w:pPr><w:spacing w:before=\"180\" w:after=\"90\"/></w:pPr>"
        "<w:rPr><w:b/><w:sz w:val=\"24\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="BodyText">'
        '<w:name w:val="Body Text"/>'
        "<w:pPr><w:spacing w:after=\"90\"/></w:pPr>"
        "<w:rPr><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="Code">'
        '<w:name w:val="Code"/>'
        "<w:pPr><w:spacing w:before=\"0\" w:after=\"0\"/>"
        '<w:shd w:val="clear" w:color="auto" w:fill="111827"/>'
        "</w:pPr>"
        '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
        '<w:color w:val="FFFFFF"/><w:sz w:val="20"/></w:rPr>'
        "</w:style>"
        '<w:style w:type="paragraph" w:styleId="ListParagraph">'
        '<w:name w:val="List Paragraph"/>'
        "<w:pPr><w:ind w:left=\"360\"/><w:spacing w:after=\"60\"/></w:pPr>"
        "<w:rPr><w:sz w:val=\"22\"/></w:rPr>"
        "</w:style>"
        "</w:styles>"
    )
