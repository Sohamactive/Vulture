from fastapi import APIRouter, Depends, HTTPException, status

from app.agents.devsecops_agent import run_devsecops_agent
from app.api.dependencies import get_current_user
from app.api.schemas import ApiResponse, ChatMessageOut, ChatMessageRequest
from app.storage import crud
from app.storage.db import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


def _to_chat_message_out(message) -> ChatMessageOut:
    return ChatMessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at.isoformat() if message.created_at else None,
    )


@router.get("/{scan_id}/history", response_model=ApiResponse)
async def chat_history(
    scan_id: str,
    user=Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    scan = await crud.get_scan_model(session, scan_id, user.id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    chat_session = await crud.get_or_create_chat_session(session, scan_id, user.id)
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Chat session error")

    messages = await crud.list_chat_messages(session, chat_session.id)
    return ApiResponse(data=[_to_chat_message_out(msg) for msg in messages])


@router.post("/{scan_id}/message", response_model=ApiResponse)
async def chat_message(
    scan_id: str,
    payload: ChatMessageRequest,
    user=Depends(get_current_user),
    session=Depends(get_db),
) -> ApiResponse:
    if not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message must not be empty")

    scan = await crud.get_scan_model(session, scan_id, user.id)
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    chat_session = await crud.get_or_create_chat_session(session, scan_id, user.id)
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Chat session error")

    await crud.create_chat_message(session, chat_session.id, "user", payload.message.strip())

    report_result = await crud.get_scan_report(session, scan_id, user.id)
    if not report_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    report, issues = report_result

    report_context = {
        "scan_id": report.id,
        "repo": report.repo_full_name,
        "branch": report.branch,
        "security_score": report.security_score,
        "summary": report.summary or {},
        "issues": [issue.model_dump() for issue in issues],
    }

    history_messages = await crud.list_chat_messages(session, chat_session.id)
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]

    assistant = run_devsecops_agent(
        report_context, history, payload.message.strip())
    assistant_message = await crud.create_chat_message(
        session,
        chat_session.id,
        "assistant",
        assistant.get("content", ""),
    )

    return ApiResponse(data={"assistant_message": _to_chat_message_out(assistant_message)})
