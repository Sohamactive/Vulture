from fastapi import APIRouter, Depends

from app.api.dependencies import ClerkUser, get_current_user
from app.api.schemas import ApiResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=ApiResponse)
def me(user: ClerkUser = Depends(get_current_user)) -> ApiResponse:
    return ApiResponse(
        data={
            "id": user.id,
            "email": user.email,
            "username": user.username,
        }
    )
