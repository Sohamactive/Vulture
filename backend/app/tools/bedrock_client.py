import json
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError


class BedrockConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise BedrockConfigError(f"{name} is not set")
    return value


def invoke_claude_messages(
    prompt: str,
    *,
    max_tokens: int = 256,
    temperature: float = 0.2,
    model_id: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")

    resolved_model_id = model_id or _require_env("AWS_BEDROCK_MODEL_ID")
    resolved_region = region or _require_env("AWS_REGION")

    client = boto3.client("bedrock-runtime", region_name=resolved_region)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    response = client.invoke_model(
        modelId=resolved_model_id,
        body=json.dumps(body),
    )

    raw_body = response.get("body")
    if hasattr(raw_body, "read"):
        raw_body = raw_body.read()
    if isinstance(raw_body, (bytes, bytearray)):
        raw_body = raw_body.decode("utf-8")

    parsed_body: Dict[str, Any] = {}
    if raw_body:
        try:
            parsed_body = json.loads(raw_body)
        except json.JSONDecodeError:
            parsed_body = {"raw_text": raw_body}

    return {
        "model_id": resolved_model_id,
        "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
        "raw_response": parsed_body,
    }
