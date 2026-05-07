┌─────────────────────────────────────────────────────────┐
│  USER AUTHENTICATION & REPO SELECTION                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. User lands on Landing Page                         │
│     ↓                                                   │
│  2. Click "Login with GitHub"                          │
│     ↓                                                   │
│  3. Clerk OAuth redirect to GitHub                     │
│     ↓                                                   │
│  4. User authorizes Vulture app                        │
│     ↓                                                   │
│  5. Redirected to Dashboard                           │
│     ↓                                                   │
│  6. Display list of user's repositories               │
│     ↓                                                   │
│  7. User selects a repo & clicks "Scan"               │
│     ↓                                                   │
│  8. Scan Progress Page shows live terminal output     │
│     ↓                                                   │
│  9. Vulnerability Report Page displays findings       │
│                                                         │
└─────────────────────────────────────────────────────────┘

FRONTEND (Landing Page)
│
├─ User clicks [Login with GitHub]
│
└─→ Redirects to: /__/clerk-auth?redirect_url=/dashboard
    │
    └─→ User sees GitHub OAuth consent screen
        │
        └─→ User clicks "Authorize Vulture"
            │
            └─→ GitHub redirects to: /__/clerk-auth/callback?code=xxxxx
                │
                └─→ Clerk exchanges code for GitHub OAuth token
                    │
                    └─→ Clerk generates JWT token
                        │
                        └─→ Frontend receives JWT + user profile
                            │
                            └─→ Store JWT in localStorage/cookies
                                │
                                └─→ Redirect to /dashboard
// Frontend: Wrap app in <ClerkProvider>
// Backend: Validate Clerk JWT on every /api/* request


FRONTEND (/dashboard)
│
├─ On mount: GET /api/repos (with Clerk JWT header)
│   Authorization: Bearer <clerk_jwt>
│
└─→ BACKEND (/api/repos)
    │
    ├─ Verify Clerk JWT token
    │
    ├─ Extract user_id from JWT claims
    │
    ├─ Fetch user's GitHub repos:
    │  └─ GET https://api.github.com/user/repos
    │     Headers: Authorization: Bearer <github_oauth_token>
    │
    ├─ Return repos list to frontend
    │
    └─→ FRONTEND receives repo data
        │
        ├─ Display: repo name, language, last_updated, stars
        │
        └─ User selects repo → clicks [Scan Now]
            │
            └─→ POST /api/scans
                Body: { repo_url, repo_owner, repo_name, branch }



FRONTEND (/scan/{scanId})
│
├─ POST /api/scans
│  Body: {
│    "repo_url": "https://github.com/user/repo",
│    "repo_owner": "user",
│    "repo_name": "repo",
│    "branch": "main"
│  }
│
└─→ BACKEND (/api/scans - POST)
    │
    ├─ Verify Clerk JWT
    │
    ├─ Create scan record in database:
    │  {
    │    "id": "scan_uuid",
    │    "user_id": "clerk_user_id",
    │    "repo_url": "...",
    │    "status": "pending",
    │    "created_at": timestamp
    │  }
    │
    ├─ Start async scan job (background task/queue)
    │
    ├─ Return scan_id to frontend
    │
    └─→ FRONTEND receives scan_id
        │
        ├─ Store in state
        │
        ├─ Connect WebSocket: ws://localhost:8000/ws/scans/{scanId}
        │
        └─→ Listen for progress messages



BACKEND (Background Job Service)
│
├─ STEP 1: Clone Repository
│  ├─ Create temp directory: /tmp/vulture_scans/{scan_uuid}/
│  │
│  ├─ git clone --depth 1 https://github.com/user/repo.git /tmp/vulture_scans/{scan_uuid}/
│  │
│  ├─ Send WebSocket progress: { type: "log", message: "✓ Cloned repository" }
│
├─ STEP 2: AST/TreeSitter Parsing
│  ├─ Initialize TreeSitter parsers for detected languages
│  │  (Python, JavaScript/TypeScript, Java, Go, Ruby, PHP, C/C++)
│  │
│  ├─ Recursively parse all source files
│  │
│  ├─ Extract:
│  │  - Function signatures & parameters
│  │  - Import statements & dependencies
│  │  - API endpoints (Flask routes, Express routes, etc.)
│  │  - Authentication/security patterns
│  │  - Data flow & variable assignments
│  │  - Exception handling
│  │  - File paths & line numbers
│  │
│  ├─ Generate structured JSON:
│  │  {
│  │    "files": [ { "path", "language", "functions", "imports", "api_endpoints" } ],
│  │    "dependencies": [ "express@4.18.0", ... ],
│  │    "entry_points": [ "main.py", "index.js" ],
│  │    "auth_patterns": [ "jwt", "oauth2", ... ]
│  │  }
│  │
│  ├─ Send WebSocket progress: { type: "log", message: "✓ Analyzed 127 files" }
│
├─ STEP 3: Chunk & Prepare for AWS Bedrock
│  ├─ Code is large → split into chunks (e.g., 5000 token chunks)
│  │
│  ├─ Create prompts with:
│  │  - Structured code summary
│  │  - Raw code snippets
│  │  - Context: framework, dependencies, auth method
│
├─ STEP 4: Send to AWS Bedrock Claude
│  ├─ FOR EACH CHUNK:
│  │  ├─ Call AWS Bedrock Invoke Model API
│  │  │
│  │  ├─ Model: "anthropic.claude-3-sonnet-20240229-v1:0"
│  │  │ (or claude-3-opus for more accuracy)
│  │  │
│  │  ├─ Prompt Template:
│  │  │  """
│  │  │  You are a security expert. Analyze this code for vulnerabilities.
│  │  │  Identify issues matching OWASP Top 10:2025.
│  │  │  
│  │  │  For each vulnerability, provide:
│  │  │  {
│  │  │    "title": "SQL Injection",
│  │  │    "severity": "critical|high|medium|low|info",
│  │  │    "owasp_category": "A03:2025 – Injection",
│  │  │    "cwe_id": "CWE-89",
│  │  │    "cve_id": "CVE-2024-XXXXX" (if known),
│  │  │    "cvss_score": 9.1,
│  │  │    "file": "app.py",
│  │  │    "line": 42,
│  │  │    "code_snippet": "...",
│  │  │    "description": "...",
│  │  │    "remediation": ["...", "..."]
│  │  │  }
│  │  │  """
│  │  │
│  │  ├─ Parse Claude response (JSON)
│  │  │
│  │  └─ Save findings to database
│  │
│  └─ Send WebSocket: { type: "log", message: "✓ Analyzed chunk 3/5" }
│
├─ STEP 5: Aggregate & Generate Report
│  ├─ Merge findings from all chunks
│  │
│  ├─ Deduplicate similar issues
│  │
│  ├─ Calculate severity summary:
│  │  { critical: 3, high: 7, medium: 12, low: 24 }
│  │
│  ├─ Calculate overall security score (0-100)
│  │
│  ├─ Store complete report in database
│
├─ STEP 6: Cleanup
│  ├─ Remove /tmp/vulture_scans/{scan_uuid}/ directory
│  │
│  ├─ Mark scan as "completed"
│  │
│  └─ Send WebSocket: { type: "complete", data: { scan_id, report_url } }
│
└─→ FRONTEND receives complete event
    │
    ├─ Auto-redirect to /report/{scanId}
    │
    └─ Display full vulnerability report



FRONTEND (/report/{scanId})
│
├─ GET /api/scans/{scanId}/vulnerabilities
│  Authorization: Bearer <clerk_jwt>
│
└─→ BACKEND (/api/scans/{scanId}/vulnerabilities - GET)
    │
    ├─ Verify JWT & ownership
    │
    ├─ Fetch report from database
    │
    ├─ Return:
    │  {
    │    "id": "scan_uuid",
    │    "summary": {
    │      "critical": 3,
    │      "high": 7,
    │      "medium": 12,
    │      "low": 24
    │    },
    │    "security_score": 42,
    │    "scanned_files": 127,
    │    "scan_duration_ms": 285000,
    │    "issues": [
    │      {
    │        "id": "vuln_1",
    │        "severity": "critical",
    │        "title": "SQL Injection",
    │        "description": "...",
    │        "owasp_category": "A03",
    │        "cwe_id": "CWE-89",
    │        "cvss_score": 9.1,
    │        "file": "api/users.py",
    │        "line": 42,
    │        "code_snippet": "SELECT * FROM users WHERE id = ' + user_input + '",
    │        "remediation": [
    │          "Use parameterized queries",
    │          "Implement input validation",
    │          "Apply principle of least privilege"
    │        ]
    │      },
    │      ...
    │    ]
    │  }
    │
    └─→ FRONTEND displays:
        │
        ├─ Report Card (summary):
        │  ┌──────────┬──────────┬──────────┬─────────┐
        │  │CRITICAL │   HIGH   │  MEDIUM  │   LOW   │
        │  │    3     │    7     │   12     │   24    │
        │  │  🔴       │  🟠       │  🟡       │  🟢      │
        │  └──────────┴──────────┴──────────┴─────────┘
        │
        ├─ Severity Donut Chart (Recharts)
        │
        ├─ OWASP Top 10 Radar Chart (Recharts)
        │
        ├─ Issue List (Jira-style):
        │  • Click issue → expand details
        │  • Show code snippet with syntax highlighting
        │  • Display remediation steps
        │  • Filter by severity
        │
        └─ Export Options:
           ├─ Export PDF
           └─ Open in Jira (if configured)


POST /api/auth/clerk-webhook
  - Webhook from Clerk to sync user creation/updates
  - No auth required (verified via Clerk signing key)

GET /api/auth/me
  - Headers: Authorization: Bearer <clerk_jwt>
  - Returns: { user_id, email, github_username, avatar_url }
  
GET /api/repos
  - Headers: Authorization: Bearer <clerk_jwt>
  - Query params: page=1, limit=20, search="repo_name"
  - Returns: { repos: [{ id, name, url, language, stars, last_updated }] }

GET /api/repos/{owner}/{repo}
  - Headers: Authorization: Bearer <clerk_jwt>
  - Returns: { name, url, description, language, size_kb, default_branch }

POST /api/scans
  - Headers: Authorization: Bearer <clerk_jwt>
  - Body: { repo_url, repo_owner, repo_name, branch }
  - Returns: { scan_id, status, created_at }

GET /api/scans
  - Headers: Authorization: Bearer <clerk_jwt>
  - Query params: page=1, limit=20
  - Returns: { scans: [{ id, repo_name, status, created_at }] }

GET /api/scans/{scanId}
  - Headers: Authorization: Bearer <clerk_jwt>
  - Returns: { id, repo_name, status, progress, created_at }

GET /api/scans/{scanId}/vulnerabilities
  - Headers: Authorization: Bearer <clerk_jwt>
  - Returns: vulnerability report (full details above)

DELETE /api/scans/{scanId}
  - Headers: Authorization: Bearer <clerk_jwt>
  - Deletes scan record & temp files

WS /ws/scans/{scanId}

MESSAGES SENT (Server → Client):
{
  "type": "log",
  "message": "✓ Cloned repository"
}

{
  "type": "progress",
  "percentage": 45,
  "current_phase": "Analyzing with AWS Bedrock"
}

{
  "type": "complete",
  "data": { scan_id, severity_summary }
}

{
  "type": "error",
  "error": "Repository size exceeds 500MB limit"
}

Layer	Technology
Frontend	React 18 + Vite, React Router v6, Zustand, Three.js/React-Three-Fiber
Authentication	Clerk (JWT), GitHub OAuth
Backend	FastAPI (Python), Uvicorn
Code Analysis	Tree-sitter (multi-language AST parsing)
AI Vulnerability Detection	AWS Bedrock (Claude 3 Sonnet/Opus)
Database	PostgreSQL or MongoDB
Real-time	WebSocket (FastAPI with websockets)
Async Jobs	Celery + Redis (or FastAPI BackgroundTasks)
External APIs	GitHub API, Clerk API
Deployment	Docker, AWS (EC2/ECS), or Vercel/Railway


# Database Schema

-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY,
  clerk_id VARCHAR UNIQUE NOT NULL,
  email VARCHAR UNIQUE NOT NULL,
  github_username VARCHAR,
  github_oauth_token VARCHAR ENCRYPTED,
  avatar_url VARCHAR,
  created_at TIMESTAMP
);

-- Scans
CREATE TABLE scans (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id),
  repo_url VARCHAR,
  repo_name VARCHAR,
  repo_owner VARCHAR,
  status ENUM('pending', 'in_progress', 'completed', 'failed'),
  progress INT DEFAULT 0,
  created_at TIMESTAMP,
  completed_at TIMESTAMP,
  error_message TEXT
);

-- Vulnerabilities
CREATE TABLE vulnerabilities (
  id UUID PRIMARY KEY,
  scan_id UUID NOT NULL REFERENCES scans(id),
  severity ENUM('critical', 'high', 'medium', 'low', 'info'),
  title VARCHAR,
  description TEXT,
  owasp_category VARCHAR,
  cwe_id VARCHAR,
  cve_id VARCHAR,
  cvss_score DECIMAL,
  file_path VARCHAR,
  line_number INT,
  code_snippet TEXT,
  remediation_steps TEXT[],
  created_at TIMESTAMP
);