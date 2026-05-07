## AWS Bedrock Connectivity

This backend exposes a connectivity probe to verify AWS Bedrock Claude access.

If Bedrock fails or is not configured, the endpoint can fall back to Gemini.

### Required Environment Variables

- `AWS_BEDROCK_MODEL_ID` (example: `anthropic.claude-sonnet-4-6`)
- `AWS_BEDROCK_OPENAI_BASE_URL` (OpenAI-compatible Bedrock endpoint URL)
- `OPENAI_API_KEY` (API key or token for the OpenAI-compatible endpoint)

### Gemini Fallback (Optional)

- `GEMINI_API_KEY`
- `GEMINI_MODEL_ID` (default: `gemini-1.5-flash`)

### Endpoint

`POST /api/connectivity`

Request body:

```json
{
	"prompt": "hello from vulture",
	"max_tokens": 128,
	"temperature": 0.2
}
```

Example curl:

```bash

curl -X POST http://localhost:8000/api/connectivity \
	-H "Content-Type: application/json" \
	-d '{"prompt":"hello from vulture","max_tokens":128,"temperature":0.2}'
```

Response: `ApiResponse` wrapper containing the full raw Bedrock response.
