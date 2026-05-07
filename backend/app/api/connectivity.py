from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError
from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.api.schemas import ApiResponse, ConnectivityRequest, ErrorDetail
from app.tools.bedrock_client import BedrockConfigError, invoke_claude_messages

router = APIRouter(prefix="/connectivity", tags=["connectivity"])


@router.post("", response_model=ApiResponse)
def connectivity_check(
    payload: ConnectivityRequest,
    _user=Depends(get_current_user),
) -> ApiResponse:
    try:
        result = invoke_claude_messages(
            payload.prompt,
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
        )
        return ApiResponse(data=result)
    except BedrockConfigError as exc:
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="aws_config_error", message=str(exc)),
        )
    except (NoCredentialsError, PartialCredentialsError) as exc:
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="aws_credentials_error", message=str(exc)),
        )
    except ClientError as exc:
        message = exc.response.get("Error", {}).get("Message", str(exc))
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="aws_client_error", message=message),
        )
    except BotoCoreError as exc:
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="aws_error", message=str(exc)),
        )
    except ValueError as exc:
        return ApiResponse(
            success=False,
            error=ErrorDetail(code="invalid_request", message=str(exc)),
        )
