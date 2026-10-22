"""Authentication endpoints: user registration, credential login, and profile retrieval."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new trader user account",
)
async def register_user(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Creates a new user profile with bcrypt-hashed credentials.

    Enforces unique email constraints and multi-tenant boundary setup.
    """
    normalized_email = payload.email.lower().strip()

    # Check for duplicate user email
    existing_user_query = await db.execute(select(User).where(User.email == normalized_email))
    if existing_user_query.scalar_one_or_none():
        raise ConflictError("A user with this email address already exists")

    password_hash = hash_password(payload.password)

    new_user = User(
        email=normalized_email,
        password_hash=password_hash,
        display_name=payload.display_name.strip() if payload.display_name else None,
        base_currency=payload.base_currency.upper().strip(),
        timezone=payload.timezone.strip(),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
)
async def login_user(
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Validates user credentials and issues an RFC 7519 signed JWT access token."""
    normalized_email = payload.email.lower().strip()

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")

    access_token = create_access_token(subject=user.id)
    expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in_seconds,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated user profile",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    """Returns the profile of the verified authenticated user.

    Strictly derives identity from the validated JWT token, never
    trusting client-supplied user parameters.
    """
    return current_user
