import os
from typing import Any, Dict, Optional

import google.generativeai as genai
from openai import OpenAI


class BedrockConfigError(RuntimeError):
    pass


class GeminiConfigError(RuntimeError):
    pass


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise BedrockConfigError(f"{name} is not set")
    return value


def _require_gemini_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise GeminiConfigError(f"{name} is not set")
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

    response = client.responses.create(
        model=resolved_model_id,
        input=[{"role": "user", "content": prompt}],
        max_output_tokens=max_tokens,
        temperature=temperature,
    )

    raw_response: Dict[str, Any]
    if hasattr(response, "model_dump"):
        raw_response = response.model_dump()
    elif hasattr(response, "dict"):
        raw_response = response.dict()
    else:
        raw_response = {"response": response}

    return {
        "model_id": resolved_model_id,
        "request_id": getattr(response, "id", None),
        "raw_response": raw_response,
    }


def invoke_gemini_text(
    prompt: str,
    *,
    max_tokens: int = 256,
    temperature: float = 0.2,
    model_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not prompt or not prompt.strip():
        raise ValueError("prompt must not be empty")

    api_key = _require_gemini_env("GEMINI_API_KEY")
    resolved_model_id = model_id or os.getenv(
        "GEMINI_MODEL_ID", "gemini-1.5-flash")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(resolved_model_id)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )

    raw_response: Dict[str, Any]
    if hasattr(response, "to_dict"):
        raw_response = response.to_dict()
    else:
        raw_response = {"text": getattr(response, "text", None)}

    return {
        "model_id": resolved_model_id,
        "request_id": getattr(response, "request_id", None),
        "raw_response": raw_response,
        "text": getattr(response, "text", None),
    }
