from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.api.schemas import ApiResponse, ScanReport
from app.export.report_generator import generate_report
from app.storage import crud
from app.storage.db import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


def _read_report_meta(summary: dict | None) -> tuple[int | None, int | None]:
    if not summary:
        return None, None
    scanned_files = summary.get("scanned_files")
    scan_duration_ms = summary.get("scan_duration_ms")
    return scanned_files, scan_duration_ms


@router.get("/{scan_id}/vulnerabilities", response_model=ApiResponse)
async def get_scan_report(
    scan_id: str,
    user=Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    result = await crud.get_scan_report(session, scan_id, user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )
    scan, issues = result
    scanned_files, scan_duration_ms = _read_report_meta(scan.summary)
    return ApiResponse(
        data=ScanReport(
            id=scan.id,
            summary=scan.summary or {
                "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            security_score=scan.security_score,
            scanned_files=scanned_files,
            scan_duration_ms=scan_duration_ms,
            issues=issues,
        )
    )


@router.get("/{scan_id}/export", response_model=ApiResponse)
async def export_scan_report(
    scan_id: str,
    export_format: str = Query(default="json", pattern="^(json|pdf|docx)$"),
    user=Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    result = await crud.get_scan_report(session, scan_id, user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    scan, issues = result
    scanned_files, scan_duration_ms = _read_report_meta(scan.summary)
    report = ScanReport(
        id=scan.id,
        summary=scan.summary or {"critical": 0,
                                 "high": 0, "medium": 0, "low": 0, "info": 0},
        security_score=scan.security_score,
        scanned_files=scanned_files,
        scan_duration_ms=scan_duration_ms,
        issues=issues,
    )
    exported = generate_report(
        report=report.model_dump(), export_format=export_format)
    return ApiResponse(data=exported)
