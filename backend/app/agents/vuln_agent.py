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

	print(f"[AI MODEL] Creating LLM: model={bedrock_model}, base_url={openai_base_url}")
	print(f"[AI MODEL] API key set: {bool(openai_api_key)}, Base URL set: {bool(openai_base_url)}")

	if not openai_base_url or not openai_api_key:
		print("[AI MODEL] ❌ Bedrock not configured!")
		raise ValueError(
			"Bedrock not configured. Set OPENAI_BASE_URL and OPENAI_API_KEY in backend/.env"
		)

	from langchain_openai import ChatOpenAI

	print(f"[AI MODEL] ✓ LLM client created successfully")
	return ChatOpenAI(
		model=bedrock_model,
		api_key=openai_api_key,
		base_url=openai_base_url,
		temperature=0,
	)


def run_vuln_agent(state: dict) -> dict[str, Any]:
	print("[AI MODEL] ▶ run_vuln_agent called — invoking LLM...")
	logger.info("[vuln_agent] invoking LLM")

	llm = _create_llm()
	messages = build_vuln_agent_messages(state)
	print(f"[AI MODEL] Sending {len(messages)} messages to LLM")

	response = llm.invoke(messages)
	raw_text = _extract_response_text(response.content)
	print(f"[AI MODEL] ✓ LLM response received — {len(raw_text)} chars")

	result = _parse_llm_json(raw_text)
	findings_count = len(result.get("findings", []))
	print(f"[AI MODEL] ✓ Parsed {findings_count} findings from LLM response")
	return result
