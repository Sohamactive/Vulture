import json
import os
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel


class ClerkUser(BaseModel):
    id: str
    email: Optional[str] = None
    username: Optional[str] = None
    github_token: Optional[str] = None
    claims: Dict[str, Any]


_jwks_client: Optional[jwt.PyJWKClient] = None


def _get_jwks_url() -> str:
    jwks_url = os.getenv("CLERK_JWKS_URL")
    if jwks_url:
        return jwks_url

    issuer = os.getenv("CLERK_ISSUER")
    if issuer:
        return issuer.rstrip("/") + "/.well-known/jwks.json"

    raise RuntimeError("CLERK_JWKS_URL or CLERK_ISSUER must be set")


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(_get_jwks_url())
    return _jwks_client


def _decode_clerk_token(token: str) -> Dict[str, Any]:
    try:
        jwk_client = _get_jwks_client()
        signing_key = jwk_client.get_signing_key_from_jwt(token)
        audience = os.getenv("CLERK_AUDIENCE")
        issuer = os.getenv("CLERK_ISSUER")
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        ) from exc


def _extract_github_token(claims: Dict[str, Any]) -> Optional[str]:
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
    async def __call__(self, request) -> Dict[str, Any]:
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

    return ClerkUser(
        id=user_id,
        email=claims.get("email"),
        username=claims.get("username"),
        github_token=_extract_github_token(claims),
        claims=claims,
    )


def get_github_token(user: ClerkUser = Depends(get_current_user)) -> str:
    if not user.github_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub token is missing from Clerk metadata",
        )
    return user.github_token
