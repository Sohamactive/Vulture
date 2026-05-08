import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.agents.orchestrator import start_scan
from app.api.dependencies import ClerkUser, get_current_user
from app.api.schemas import ApiResponse, ScanCreateRequest, ScanSummary, VulnerabilitySummary
from app.storage import crud
from app.storage.db import AsyncSessionLocal, get_db

router = APIRouter(prefix="/scans", tags=["scans"])


def _clone_repo(repo_url: str, branch: str, dest: str) -> None:
    """Clone a git repository into dest directory."""
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--branch", branch,
        "--single-branch",
        repo_url,
        dest,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        # Try without --branch (some repos use main vs master)
        cmd_fallback = [
            "git", "clone",
            "--depth", "1",
            repo_url,
            dest,
        ]
        result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"git clone failed: {result.stderr.strip()}")


def _map_finding_to_vuln(finding: dict, scan_id: str) -> VulnerabilitySummary:
    """Map a single finding from the orchestrator report to a VulnerabilitySummary."""
    severity = str(finding.get("severity", "low")).lower()
    # Normalize severity values
    if severity not in ("critical", "high", "medium", "low", "info"):
        severity = "medium"

    # Normalize remediation: orchestrator may return str or list
    raw_remediation = finding.get("remediation") or finding.get("fix")
    if isinstance(raw_remediation, str):
        remediation = [raw_remediation]
    elif isinstance(raw_remediation, list):
        remediation = raw_remediation
    else:
        remediation = None

    return VulnerabilitySummary(
        id=finding.get("id") or str(uuid.uuid4()),
        title=finding.get("title") or finding.get("rule_id") or "Untitled Finding",
        severity=severity,
        detection_source=finding.get("detection_source") or finding.get("source") or "ai",
        owasp_category=finding.get("owasp_category"),
        cwe_id=finding.get("cwe_id") or finding.get("cwe"),
        file_path=finding.get("file_path") or finding.get("file"),
        line_start=finding.get("line_start") or finding.get("line"),
        line_end=finding.get("line_end"),
        code_snippet=finding.get("code_snippet") or finding.get("snippet"),
        description=finding.get("description"),
        remediation=remediation,
    )


async def _run_scan(scan_id: str, payload: ScanCreateRequest, user_id: str) -> None:
    tmp_dir = None
    try:
        # --- Stage 1: Cloning ---
        async with AsyncSessionLocal() as session:
            await crud.update_scan_status(session, scan_id, user_id, status="cloning")

        tmp_dir = tempfile.mkdtemp(prefix=f"vulture_{scan_id[:8]}_")
        repo_dir = os.path.join(tmp_dir, "repo")

        await run_in_threadpool(_clone_repo, payload.repo_url, payload.branch, repo_dir)

        # --- Stage 2: Semgrep scanning ---
        async with AsyncSessionLocal() as session:
            await crud.update_scan_status(session, scan_id, user_id, status="semgrep_scanning")

        # --- Stage 3+4: Parsing + Analyzing via orchestrator ---
        async with AsyncSessionLocal() as session:
            await crud.update_scan_status(session, scan_id, user_id, status="parsing")

        # Run the orchestrator pipeline
        final_report = {}
        last_stage = "init"

        async for event in start_scan(repo_path=repo_dir, rules="auto"):
            stage = event.get("stage", "")

            # Track stage transitions for DB status updates
            if stage == "ast_parser" and last_stage != "parsing":
                last_stage = "parsing"
            elif stage == "agent" and last_stage != "analyzing":
                last_stage = "analyzing"
                async with AsyncSessionLocal() as session:
                    await crud.update_scan_status(session, scan_id, user_id, status="analyzing")

            # Capture the final report
            if stage == "final_report":
                final_report = event.get("report", {})

        # --- Stage 5: Process results ---
        findings = final_report.get("findings", [])
        issues: List[VulnerabilitySummary] = [
            _map_finding_to_vuln(f, scan_id) for f in findings
        ]

        # Build severity summary from actual findings
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in issues:
            sev = issue.severity.lower()
            if sev in summary:
                summary[sev] += 1

        # Compute security score from risk_score (0.0 - 10.0 → 100 - 0)
        risk_score = float(final_report.get("risk_score", 0.0))
        security_score = max(0, min(100, int(100 - (risk_score * 10))))

        # Persist results
        async with AsyncSessionLocal() as session:
            await crud.update_scan_status(
                session,
                scan_id,
                user_id,
                status="completed",
                security_score=security_score,
                summary=summary,
            )
            await crud.replace_scan_report(
                session,
                scan_id,
                user_id,
                summary=summary,
                security_score=security_score,
                issues=issues,
            )

    except Exception as exc:
        # Mark scan as failed
        try:
            async with AsyncSessionLocal() as session:
                await crud.update_scan_status(
                    session, scan_id, user_id, status="failed"
                )
        except Exception:
            pass
        # Re-raise so BackgroundTasks logs the exception
        raise

    finally:
        # Clean up temp directory
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


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
