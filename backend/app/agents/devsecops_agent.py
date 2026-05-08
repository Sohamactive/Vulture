from __future__ import annotations

import os
from typing import Any, List

from app.logger import get_logger
from app.prompts.devsecops_prompts import build_devsecops_messages

logger = get_logger(__name__)


def _extract_response_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text") or str(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content)


def _create_llm():
    openai_base_url = os.environ.get("OPENAI_BASE_URL", "").strip().strip('"')
    openai_api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    bedrock_model = os.environ.get(
        "AWS_BEDROCK_MODEL_ID",
        "mistral.mistral-large-3-675b-instruct",
    )

    if not openai_base_url or not openai_api_key:
        raise ValueError(
            "Bedrock not configured. Set OPENAI_BASE_URL and OPENAI_API_KEY in backend/.env"
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=bedrock_model,
        api_key=openai_api_key,
        base_url=openai_base_url,
        temperature=0.1,
    )


def run_devsecops_agent(
    report_context: dict,
    history: List[dict],
    user_message: str,
) -> dict[str, Any]:
    logger.info("[devsecops_agent] invoking LLM")

    llm = _create_llm()
    messages = build_devsecops_messages(report_context, history, user_message)
    response = llm.invoke(messages)
    content = _extract_response_text(response.content)

    return {"content": content}
