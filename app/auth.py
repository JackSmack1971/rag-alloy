"""Authentication dependency for FastAPI endpoints."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from app.settings import Settings, get_settings


def require_auth(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate bearer token based on ``APP_AUTH_MODE``."""
    if settings.app_auth_mode == "none":
        return
    if settings.app_auth_mode == "token":
        if (
            authorization is None
            or not authorization.startswith("Bearer ")
            or authorization.split(" ", 1)[1] != settings.app_token
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid auth mode")
