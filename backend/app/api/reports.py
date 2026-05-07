from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.api.schemas import ApiResponse, ScanReport
from app.api.scans import _SCAN_REPORTS
from app.export.report_generator import generate_report

router = APIRouter(prefix="/scans", tags=["reports"])


@router.get("/{scan_id}/vulnerabilities", response_model=ApiResponse)
def get_scan_report(scan_id: str, _user=Depends(get_current_user)) -> ApiResponse:
    report = _SCAN_REPORTS.get(scan_id)
    if not report:
        empty = ScanReport(id=scan_id, summary={
                           "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0})
        return ApiResponse(data=empty)
    return ApiResponse(data=ScanReport(**report))


@router.get("/{scan_id}/export", response_model=ApiResponse)
def export_scan_report(
    scan_id: str,
    export_format: str = Query(default="json", pattern="^(json|pdf)$"),
    _user=Depends(get_current_user),
) -> ApiResponse:
    report = _SCAN_REPORTS.get(scan_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    exported = generate_report(report=report, export_format=export_format)
    return ApiResponse(data=exported)
