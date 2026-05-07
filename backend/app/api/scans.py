import uuid
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.agents.orchestrator import start_scan
from app.api.dependencies import ClerkUser, get_current_user
from app.api.schemas import ApiResponse, ScanCreateRequest, ScanSummary

router = APIRouter(prefix="/scans", tags=["scans"])

_SCAN_STORE: Dict[str, ScanSummary] = {}
_SCAN_REPORTS: Dict[str, dict] = {}


def _run_scan(scan_id: str, payload: ScanCreateRequest, user: ClerkUser) -> None:
    summary = _SCAN_STORE[scan_id]
    summary.status = "cloning"
    _SCAN_STORE[scan_id] = summary

    start_scan(scan_id=scan_id, repo_url=payload.repo_url,
               branch=payload.branch, user_id=user.id)

    summary.status = "completed"
    summary.security_score = 100
    summary.summary = {"critical": 0, "high": 0,
                       "medium": 0, "low": 0, "info": 0}
    _SCAN_STORE[scan_id] = summary

    _SCAN_REPORTS[scan_id] = {
        "id": scan_id,
        "summary": summary.summary,
        "security_score": summary.security_score,
        "issues": [],
    }


@router.post("", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED)
def create_scan(
    payload: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(get_current_user),
) -> ApiResponse:
    scan_id = str(uuid.uuid4())
    summary = ScanSummary(
        id=scan_id,
        repo_full_name=f"{payload.repo_owner}/{payload.repo_name}",
        repo_url=payload.repo_url,
        branch=payload.branch,
        status="pending",
    )
    _SCAN_STORE[scan_id] = summary
    background_tasks.add_task(_run_scan, scan_id, payload, user)
    return ApiResponse(data=summary)


@router.get("/history", response_model=ApiResponse)
def scan_history(user: ClerkUser = Depends(get_current_user)) -> ApiResponse:
    scans: List[ScanSummary] = [scan for scan in _SCAN_STORE.values() if scan]
    return ApiResponse(data=scans)


@router.get("/{scan_id}", response_model=ApiResponse)
def get_scan(scan_id: str, user: ClerkUser = Depends(get_current_user)) -> ApiResponse:
    summary = _SCAN_STORE.get(scan_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return ApiResponse(data=summary)


@router.post("/{scan_id}/rerun", response_model=ApiResponse)
def rerun_scan(
    scan_id: str,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(get_current_user),
) -> ApiResponse:
    summary = _SCAN_STORE.get(scan_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    payload = ScanCreateRequest(
        repo_url=summary.repo_url,
        repo_owner=summary.repo_full_name.split("/")[0],
        repo_name=summary.repo_full_name.split("/")[1],
        branch=summary.branch,
    )
    summary.status = "pending"
    _SCAN_STORE[scan_id] = summary
    background_tasks.add_task(_run_scan, scan_id, payload, user)
    return ApiResponse(data=summary)
