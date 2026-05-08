from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/scans/{scan_id}")
async def scan_progress(websocket: WebSocket, scan_id: str) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "log", "message": "connected", "scan_id": scan_id})
    await websocket.send_json({"type": "log", "message": "scan queued"})
    await websocket.send_json({"type": "complete", "scan_id": scan_id})
    await websocket.close()
