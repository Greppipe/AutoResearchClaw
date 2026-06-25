import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()
security_scheme = HTTPBearer()


async def get_clerk_jwks() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.CLERK_JWKS_URL)
        response.raise_for_status()
        return response.json()


async def verify_clerk_token(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
) -> dict:
    token = credentials.credentials
    try:
        jwks = await get_clerk_jwks()
        keys = jwks.get("keys", [])

        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        signing_key = next((k for k in keys if k["kid"] == kid), None)

        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload

    except JWTError as e:
        logger.error("JWT verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def get_user_id(payload: dict) -> str:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token",
        )
    return user_id


def require_role(required_role: str):
    async def _check_role(payload: dict = Security(verify_clerk_token)) -> dict:
        roles = payload.get("metadata", {}).get("roles", ["user"])
        role_hierarchy = {"user": 0, "researcher": 1, "editor": 2, "admin": 3}
        user_max_role = max((role_hierarchy.get(r, 0) for r in roles), default=0)
        required_level = role_hierarchy.get(required_role, 0)

        if user_max_role < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return payload

    return _check_role
