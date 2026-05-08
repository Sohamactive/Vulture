from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None


class ConnectivityRequest(BaseModel):
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.2


class RepoSummary(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    language: Optional[str] = None
    stars: int = 0
    updated_at: Optional[str] = None
    visibility: str = "public"
    default_branch: Optional[str] = None
    html_url: Optional[str] = None


class ScanCreateRequest(BaseModel):
    repo_url: str
    repo_owner: str
    repo_name: str
    branch: str = Field(default="main")


class ScanSummary(BaseModel):
    id: str
    repo_full_name: str
    repo_url: str
    branch: str
    status: str
    security_score: Optional[int] = None
    summary: Optional[dict] = None


class VulnerabilitySummary(BaseModel):
    id: str
    title: str
    severity: str
    detection_source: str
    owasp_category: Optional[str] = None
    cwe_id: Optional[str] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[List[str]] = None
    confidence_score: Optional[int] = None
    exploitability: Optional[str] = None
    business_impact: Optional[str] = None
    false_positive_risk: Optional[str] = None
    filepath: Optional[str] = None
    line_numbers: Optional[List[int]] = None
    attack_scenario: Optional[str] = None
    exploit_chain: Optional[List[str]] = None
    remediation_priority: Optional[str] = None
    reachability: Optional[str] = None
    finding_metadata: Optional[dict] = None


class ScanReport(BaseModel):
    id: str
    summary: dict
    security_score: Optional[int] = None
    scanned_files: Optional[int] = None
    scan_duration_ms: Optional[int] = None
    issues: List[VulnerabilitySummary] = Field(default_factory=list)


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: Optional[str] = None


class ChatMessageRequest(BaseModel):
    message: str
