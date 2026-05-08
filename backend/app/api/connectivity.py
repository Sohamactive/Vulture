from fastapi import APIRouter, HTTPException, status
from openai import APIConnectionError, APIError, AuthenticationError, BadRequestError, RateLimitError

from app.api.schemas import ApiResponse, ConnectivityRequest
from app.tools.bedrock_client import BedrockConfigError, invoke_claude_messages


router = APIRouter(prefix="/connectivity", tags=["connectivity"])


@router.post("", response_model=ApiResponse)
def connectivity_check(
    payload: ConnectivityRequest,
) -> ApiResponse:
    try:
        result = invoke_claude_messages(
            payload.prompt,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
        )
        result["provider"] = "bedrock"
        return ApiResponse(data=result)
    except (
        BedrockConfigError,
        AuthenticationError,
        BadRequestError,
        RateLimitError,
        APIConnectionError,
        APIError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=ErrorDetail(code="bedrock_error",
                               message=str(exc)).model_dump(),
        ) from exc
