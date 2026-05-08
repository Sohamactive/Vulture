from typing import Iterable, List, Optional, Tuple

from sqlalchemy import delete, select
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
    )


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
    for issue in issues:
        session.add(
            Vulnerability(
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
        )
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
