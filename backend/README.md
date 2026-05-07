## AWS Bedrock Connectivity

This backend exposes a connectivity probe to verify AWS Bedrock Claude access.

### Required Environment Variables

- `AWS_REGION` (example: `ap-south-1`)
- `AWS_BEDROCK_MODEL_ID` (example: `anthropic.claude-sonnet-4-6`)

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

Example curl (requires Clerk JWT):

```bash
curl -X POST http://localhost:8000/api/connectivity \
	-H "Authorization: Bearer <clerk_jwt>" \
	-H "Content-Type: application/json" \
	-d '{"prompt":"hello from vulture","max_tokens":128,"temperature":0.2}'
```

Response: `ApiResponse` wrapper containing the full raw Bedrock response.
