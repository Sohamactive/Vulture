import uuid
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.agents.orchestrator import start_scan
from app.api.dependencies import ClerkUser, get_current_user
from app.api.schemas import ApiResponse, ScanCreateRequest, ScanSummary, VulnerabilitySummary
from app.storage import crud
from app.storage.db import AsyncSessionLocal, get_db

router = APIRouter(prefix="/scans", tags=["scans"])


async def _run_scan(scan_id: str, payload: ScanCreateRequest, user_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await crud.update_scan_status(session, scan_id, user_id, status="cloning")

    await run_in_threadpool(
        start_scan,
        scan_id=scan_id,
        repo_url=payload.repo_url,
        branch=payload.branch,
        user_id=user_id,
    )

    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    issues: List[VulnerabilitySummary] = []

    async with AsyncSessionLocal() as session:
        await crud.update_scan_status(
            session,
            scan_id,
            user_id,
            status="completed",
            security_score=100,
            summary=summary,
        )
        await crud.replace_scan_report(
            session,
            scan_id,
            user_id,
            summary=summary,
            security_score=100,
            issues=issues,
        )


@router.post("", response_model=ApiResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_scan(
    payload: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    scan_id = str(uuid.uuid4())
    summary = await crud.create_scan(session, scan_id, payload, user.id)
    background_tasks.add_task(_run_scan, scan_id, payload, user.id)
    return ApiResponse(data=summary)


@router.get("/history", response_model=ApiResponse)
async def scan_history(
    user: ClerkUser = Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    scans = await crud.list_scans(session, user.id)
    return ApiResponse(data=scans)


@router.get("/{scan_id}", response_model=ApiResponse)
async def get_scan(
    scan_id: str,
    user: ClerkUser = Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    summary = await crud.get_scan(session, scan_id, user.id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return ApiResponse(data=summary)


@router.post("/{scan_id}/rerun", response_model=ApiResponse)
async def rerun_scan(
    scan_id: str,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    summary = await crud.get_scan(session, scan_id, user.id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    payload = ScanCreateRequest(
        repo_url=summary.repo_url,
        repo_owner=summary.repo_full_name.split("/")[0],
        repo_name=summary.repo_full_name.split("/")[1],
        branch=summary.branch,
    )
    summary = await crud.update_scan_status(session, scan_id, user.id, status="pending")
    background_tasks.add_task(_run_scan, scan_id, payload, user.id)
    return ApiResponse(data=summary)
