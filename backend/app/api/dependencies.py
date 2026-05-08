import json
import os
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.requests import Request as StarletteRequest
from pydantic import BaseModel


class ClerkUser(BaseModel):
    id: str
    email: Optional[str] = None
    username: Optional[str] = None
    github_token: Optional[str] = None
    claims: Dict[str, Any]


def _get_jwks_url() -> str:
    jwks_url = os.getenv("CLERK_JWKS_URL")
    if jwks_url:
        return jwks_url

    issuer = os.getenv("CLERK_ISSUER")
    if issuer:
        return issuer.rstrip("/") + "/.well-known/jwks.json"

    raise RuntimeError("CLERK_JWKS_URL or CLERK_ISSUER must be set")


def _get_jwks_client() -> jwt.PyJWKClient:
    """Create a fresh JWKS client each time to avoid stale key caching."""
    return jwt.PyJWKClient(_get_jwks_url())


def _decode_clerk_token(token: str) -> Dict[str, Any]:
    try:
        jwk_client = _get_jwks_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        audience = os.getenv("CLERK_AUDIENCE") or None
        issuer = os.getenv("CLERK_ISSUER") or None

        decode_options = {}
        if not audience:
            decode_options["verify_aud"] = False

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options=decode_options,
        )
        print(f"[AUTH OK] sub={claims.get('sub')}")
        return claims
    except jwt.PyJWTError as exc:
        print(f"[AUTH ERROR] JWT decode failed: {type(exc).__name__}: {exc}")
        # Show which issuer was expected vs what's in the token
        try:
            unverified = jwt.decode(token, options={"verify_signature": False, "verify_aud": False, "verify_iss": False, "verify_exp": False})
            print(f"[AUTH ERROR] Token iss={unverified.get('iss')}, expected iss={os.getenv('CLERK_ISSUER')}")
            print(f"[AUTH ERROR] Token exp={unverified.get('exp')}, sub={unverified.get('sub')}")
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {type(exc).__name__}",
        ) from exc


def _fetch_github_token_from_clerk(user_id: str) -> Optional[str]:
    """Fetch the user's GitHub OAuth token via the Clerk Backend API."""
    secret_key = os.getenv("CLERK_SECRET_KEY")
    if not secret_key:
        print("[AUTH] CLERK_SECRET_KEY not set — cannot fetch GitHub OAuth token")
        return None

    url = f"https://api.clerk.com/v1/users/{user_id}/oauth_access_tokens/oauth_github"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "User-Agent": "Vulture/1.0",
        },
    )
    try:
        with urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
        if isinstance(data, list) and len(data) > 0:
            token = data[0].get("token")
            if token:
                print(f"[AUTH] Got GitHub token for user {user_id}")
                return token
        print(f"[AUTH] No GitHub token in Clerk response for user {user_id}: {data}")
    except Exception as exc:
        # Read the error body for details
        error_body = ""
        if hasattr(exc, "read"):
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass
        print(f"[AUTH] Failed to fetch GitHub token from Clerk API: {exc}")
        if error_body:
            print(f"[AUTH] Clerk error response: {error_body}")
    return None


def _extract_github_token(claims: Dict[str, Any]) -> Optional[str]:
    """Try to extract GitHub token from JWT private_metadata (legacy approach)."""
    metadata = claims.get("private_metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = None
    if isinstance(metadata, dict):
        for key in ("github_oauth_token", "github_access_token"):
            token = metadata.get(key)
            if token:
                return token
    return None


class ClerkJWTBearer(HTTPBearer):
    async def __call__(self, request: StarletteRequest) -> Dict[str, Any]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication token",
            )
        return _decode_clerk_token(credentials.credentials)


def get_current_user(
    claims: Dict[str, Any] = Depends(ClerkJWTBearer()),
) -> ClerkUser:
    user_id = claims.get("sub") or claims.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    github_token = _extract_github_token(claims)
    if not github_token:
        github_token = _fetch_github_token_from_clerk(user_id)

    return ClerkUser(
        id=user_id,
        email=claims.get("email"),
        username=claims.get("username"),
        github_token=github_token,
        claims=claims,
    )


def get_github_token(user: ClerkUser = Depends(get_current_user)) -> str:
    if not user.github_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub token not available. Ensure you signed in with GitHub via Clerk.",
        )
    return user.github_token
