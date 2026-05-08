from typing import Iterable, List, Optional, Tuple

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ScanCreateRequest, ScanSummary, VulnerabilitySummary
from app.storage.models import Scan, Vulnerability


def _to_scan_summary(scan: Scan) -> ScanSummary:
    return ScanSummary(
        id=scan.id,
        repo_full_name=scan.repo_full_name,
        repo_url=scan.repo_url,
        branch=scan.branch,
        status=scan.status,
        security_score=scan.security_score,
        summary=scan.summary,
    )


def _to_vulnerability_summary(vuln: Vulnerability) -> VulnerabilitySummary:
    # Avoid triggering deferred column load when older DB schema lacks finding_metadata.
    metadata = vuln.__dict__.get("finding_metadata") or {}
    line_numbers = metadata.get("line_numbers")
    if not isinstance(line_numbers, list):
        line_numbers = []
    normalized_line_numbers = [int(x) for x in line_numbers if isinstance(x, int)]

    return VulnerabilitySummary(
        id=vuln.id,
        title=vuln.title,
        severity=vuln.severity,
        detection_source=vuln.detection_source,
        owasp_category=vuln.owasp_category,
        cwe_id=vuln.cwe_id,
        file_path=vuln.file_path,
        line_start=vuln.line_start,
        line_end=vuln.line_end,
        code_snippet=vuln.code_snippet,
        description=vuln.description,
        remediation=vuln.remediation,
        confidence_score=metadata.get("confidence_score"),
        exploitability=metadata.get("exploitability"),
        business_impact=metadata.get("business_impact"),
        false_positive_risk=metadata.get("false_positive_risk"),
        filepath=metadata.get("filepath") or vuln.file_path,
        line_numbers=normalized_line_numbers or None,
        attack_scenario=metadata.get("attack_scenario"),
        exploit_chain=metadata.get("exploit_chain"),
        remediation_priority=metadata.get("remediation_priority"),
        reachability=metadata.get("reachability"),
        finding_metadata=metadata or None,
    )


async def _has_finding_metadata_column(session: AsyncSession) -> bool:
    result = await session.execute(text("PRAGMA table_info(vulnerabilities)"))
    rows = result.fetchall()
    return any(len(row) > 1 and row[1] == "finding_metadata" for row in rows)


async def create_scan(
    session: AsyncSession,
    scan_id: str,
    payload: ScanCreateRequest,
    user_id: str,
) -> ScanSummary:
    scan = Scan(
        id=scan_id,
        user_id=user_id,
        repo_full_name=f"{payload.repo_owner}/{payload.repo_name}",
        repo_url=payload.repo_url,
        branch=payload.branch,
        status="pending",
    )
    session.add(scan)
    await session.commit()
    await session.refresh(scan)
    return _to_scan_summary(scan)


async def get_scan(
    session: AsyncSession,
    scan_id: str,
    user_id: str,
) -> Optional[ScanSummary]:
    result = await session.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return None
    return _to_scan_summary(scan)


async def list_scans(session: AsyncSession, user_id: str) -> List[ScanSummary]:
    result = await session.execute(
        select(Scan).where(Scan.user_id == user_id).order_by(
            Scan.created_at.desc())
    )
    scans = result.scalars().all()
    return [_to_scan_summary(scan) for scan in scans]


async def update_scan_status(
    session: AsyncSession,
    scan_id: str,
    user_id: str,
    status: str,
    security_score: Optional[int] = None,
    summary: Optional[dict] = None,
) -> Optional[ScanSummary]:
    result = await session.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return None
    scan.status = status
    if security_score is not None:
        scan.security_score = security_score
    if summary is not None:
        scan.summary = summary
    await session.commit()
    await session.refresh(scan)
    return _to_scan_summary(scan)


async def replace_scan_report(
    session: AsyncSession,
    scan_id: str,
    user_id: str,
    summary: dict,
    security_score: int,
    issues: Iterable[VulnerabilitySummary],
) -> None:
    result = await session.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return
    scan.summary = summary
    scan.security_score = security_score
    await session.execute(delete(Vulnerability).where(Vulnerability.scan_id == scan_id))
    has_finding_metadata = await _has_finding_metadata_column(session)
    for issue in issues:
        payload = dict(
            id=issue.id,
            scan_id=scan_id,
            title=issue.title,
            severity=issue.severity,
            detection_source=issue.detection_source,
            owasp_category=issue.owasp_category,
            cwe_id=issue.cwe_id,
            file_path=issue.file_path,
            line_start=issue.line_start,
            line_end=issue.line_end,
            code_snippet=issue.code_snippet,
            description=issue.description,
            remediation=issue.remediation,
        )
        if has_finding_metadata:
            payload["finding_metadata"] = issue.finding_metadata
        session.add(Vulnerability(**payload))
    await session.commit()


async def get_scan_report(
    session: AsyncSession,
    scan_id: str,
    user_id: str,
) -> Optional[Tuple[ScanSummary, List[VulnerabilitySummary]]]:
    result = await session.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return None
    issues_result = await session.execute(
        select(Vulnerability).where(Vulnerability.scan_id == scan_id)
    )
    issues = issues_result.scalars().all()
    return _to_scan_summary(scan), [_to_vulnerability_summary(issue) for issue in issues]
