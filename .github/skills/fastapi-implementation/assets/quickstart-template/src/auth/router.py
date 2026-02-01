"""Authentication router."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import schemas, service
from src.database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_data: schemas.UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Secure password (min 8 characters)
    """
    return await service.create_user(db, user_data)


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    summary="Login",
)
async def login(
    credentials: schemas.LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username and password.

    Returns an access token for authenticated requests.
    """
    return await service.authenticate_user(db, credentials)


@router.get(
    "/me",
    response_model=schemas.UserResponse,
    summary="Get current user",
)
async def get_current_user(
    user=Depends(service.get_current_active_user),
):
    """
    Get the current authenticated user's information.

    Requires: Bearer token in Authorization header.
    """
    return user
