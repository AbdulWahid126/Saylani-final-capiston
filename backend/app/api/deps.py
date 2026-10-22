"""Reusable FastAPI route dependencies for database sessions and authentication."""

import uuid
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    """Dependency that validates bearer JWT token and retrieves the authenticated user.

    Strictly enforces tenant isolation by rejecting missing, malformed,
    expired, or unverified tokens with HTTP 401.
    """
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Authentication token is required")

    token = credentials.credentials
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AuthenticationError("Authentication token missing user identifier")

    try:
        user_uuid = uuid.UUID(user_id_str)
    except (ValueError, TypeError) as exc:
        raise AuthenticationError("Malformed user identifier in token") from exc

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError("User associated with this token no longer exists")

    return user


def enforce_resource_ownership(resource_user_id: Any, current_user: User | uuid.UUID | str) -> None:
    """Validates that a resource's user_id matches the authenticated user.

    Accepts either an ORM model instance with a user_id attribute or a raw user_id.
    Raises ForbiddenError (HTTP 403) if cross-tenant access is attempted.
    """
    res_uid = getattr(resource_user_id, "user_id", resource_user_id)
    current_uid = current_user.id if isinstance(current_user, User) else current_user
    if str(res_uid) != str(current_uid):
        raise ForbiddenError("Access forbidden: you do not own this resource")
