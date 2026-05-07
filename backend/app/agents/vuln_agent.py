from __future__ import annotations

import json
import os
import re
from typing import Any

from app.logger import get_logger
from app.prompts.vuln_prompts import build_vuln_agent_messages

logger = get_logger(__name__)


def _extract_response_text(content: object) -> str:
	if isinstance(content, str):
		return content
	if isinstance(content, list):
		parts: list[str] = []
		for item in content:
			if isinstance(item, str):
				parts.append(item)
			elif isinstance(item, dict):
				parts.append(item.get("text") or str(item))
			else:
				parts.append(str(item))
		return "\n".join(parts)
	return str(content)


def _parse_llm_json(raw: str) -> dict:
	text = raw.strip()
	text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
	text = re.sub(r"\s*```$", "", text)
	text = text.strip()
	try:
		return json.loads(text)
	except json.JSONDecodeError:
		match = re.search(r"\{.*\}", text, re.DOTALL)
		if match:
			return json.loads(match.group(0))
		raise


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

	logger.info(
		"[vuln_agent] using Bedrock Mantle: model=%s, base_url=%s",
		bedrock_model,
		openai_base_url,
	)
	return ChatOpenAI(
		model=bedrock_model,
		api_key=openai_api_key,
		base_url=openai_base_url,
		temperature=0,
	)


def run_vuln_agent(state: dict) -> dict[str, Any]:
	logger.info("[vuln_agent] invoking LLM")

	llm = _create_llm()
	messages = build_vuln_agent_messages(state)
	response = llm.invoke(messages)
	raw_text = _extract_response_text(response.content)
	return _parse_llm_json(raw_text)
