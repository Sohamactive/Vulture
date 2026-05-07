import os
from typing import Any, Dict, Optional

from openai import OpenAI


class BedrockConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise BedrockConfigError(f"{name} is not set")
    return value


def _resolve_base_url() -> str:
    base_url = os.getenv("AWS_BEDROCK_OPENAI_BASE_URL") or os.getenv(
        "OPENAI_BASE_URL")
    if not base_url:
        raise BedrockConfigError(
            "AWS_BEDROCK_OPENAI_BASE_URL or OPENAI_BASE_URL is not set"
        )
    return base_url


def invoke_claude_messages(
    prompt: str,
    *,
    max_tokens: int = 256,
    temperature: float = 0.2,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")

    resolved_model_id = model_id or _require_env("AWS_BEDROCK_MODEL_ID")
    api_key = _require_env("OPENAI_API_KEY")
    base_url = _resolve_base_url()

    client = OpenAI(api_key=api_key, base_url=base_url)

    response = client.chat.completions.create(
        model=resolved_model_id,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    raw_response: Dict[str, Any]
    if hasattr(response, "model_dump"):
        raw_response = response.model_dump()
    elif hasattr(response, "dict"):
        raw_response = response.dict()
    else:
        raw_response = {"response": response}

    text = None
    if getattr(response, "choices", None):
        choice = response.choices[0]
        text = getattr(choice.message, "content", None)

    return {
        "model_id": resolved_model_id,
        "request_id": getattr(response, "id", None),
        "raw_response": raw_response,
        "text": text,
    }
