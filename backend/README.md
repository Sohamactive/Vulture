## AWS Bedrock Connectivity

This backend exposes a connectivity probe to verify AWS Bedrock Claude access.


### Required Environment Variables

- `AWS_BEDROCK_MODEL_ID` (example: `anthropic.claude-sonnet-4-6`)
- `AWS_BEDROCK_OPENAI_BASE_URL` (OpenAI-compatible Bedrock endpoint URL)
- `OPENAI_API_KEY` (API key or token for the OpenAI-compatible endpoint)

### Endpoint

`POST /api/connectivity`

## Main API Routes

- `GET /api/health`
- `GET /api/auth/me`
- `GET /api/repos`
- `POST /api/scans`
- `GET /api/scans/history`
- `GET /api/scans/{scan_id}`
- `POST /api/scans/{scan_id}/rerun`
- `GET /api/reports/{scan_id}/vulnerabilities`
- `GET /api/reports/{scan_id}/export?export_format=json|pdf`
- `WS /api/ws/scans/{scan_id}`

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
