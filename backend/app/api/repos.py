import json
from typing import List
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user, get_github_token
from app.api.schemas import ApiResponse, RepoSummary

router = APIRouter(prefix="/repos", tags=["repos"])


def _fetch_github_repos(token: str) -> List[RepoSummary]:
    request = Request(
        "https://api.github.com/user/repos?per_page=100&sort=updated",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request) as response:
        payload = json.loads(response.read().decode("utf-8"))

    repos: List[RepoSummary] = []
    for repo in payload:
        repos.append(
            RepoSummary(
                id=repo.get("id"),
                name=repo.get("name"),
                full_name=repo.get("full_name"),
                description=repo.get("description"),
                language=repo.get("language"),
                stars=repo.get("stargazers_count", 0),
                updated_at=repo.get("updated_at"),
                visibility=repo.get("visibility", "public"),
                default_branch=repo.get("default_branch"),
                html_url=repo.get("html_url"),
            )
        )
    return repos


@router.get("", response_model=ApiResponse)
def list_repos(
    user=Depends(get_current_user),
    token: str = Depends(get_github_token),
) -> ApiResponse:
    try:
        repos = _fetch_github_repos(token)
        return ApiResponse(data=repos)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to fetch repositories from GitHub",
        ) from exc
