from fastapi import APIRouter
from openai import APIConnectionError, APIError, AuthenticationError, BadRequestError, RateLimitError

from app.api.schemas import ApiResponse, ConnectivityRequest, ErrorDetail
from app.tools.bedrock_client import (
    BedrockConfigError,
    GeminiConfigError,
    invoke_claude_messages,
    invoke_gemini_text,
)

router = APIRouter(prefix="/connectivity", tags=["connectivity"])


@router.post("", response_model=ApiResponse)
def connectivity_check(
    payload: ConnectivityRequest,
) -> ApiResponse:
    bedrock_error: Exception | None = None
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
        bedrock_error = exc

    try:
        result = invoke_gemini_text(
            payload.prompt,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
        )
        result["provider"] = "gemini"
        result["fallback_from"] = "bedrock"
        result["bedrock_error"] = str(bedrock_error)
        return ApiResponse(data=result)
    except GeminiConfigError as exc:
        message = str(exc)
        if bedrock_error:
            message = f"bedrock failed: {bedrock_error}; gemini: {exc}"
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="fallback_config_error", message=message),
        )
    except Exception as exc:
        message = str(exc)
        if bedrock_error:
            message = f"bedrock failed: {bedrock_error}; gemini: {exc}"
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="fallback_error", message=message),
        )
