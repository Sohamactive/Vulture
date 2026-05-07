from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.repos import router as repos_router
from app.api.reports import router as reports_router
from app.api.scans import router as scans_router
from app.api.ws import router as ws_router
from app.api.connectivity import router as connectivity_router

api_router = APIRouter()


@api_router.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(repos_router)
api_router.include_router(scans_router)
api_router.include_router(reports_router)
api_router.include_router(ws_router)
api_router.include_router(connectivity_router)
