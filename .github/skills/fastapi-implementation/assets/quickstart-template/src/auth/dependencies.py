"""Authentication dependencies."""

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import service
from src.auth.models import User
from src.config import settings
from src.database import get_db
from src.exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user.

    Validates JWT token and returns user from database.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise UnauthorizedError("Invalid token")
        user_id = UUID(user_id_str)
    except JWTError:
        raise UnauthorizedError("Invalid token")

    user = await service.get_user_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("User not found")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to get current active user.

    Ensures user account is active.
    """
    if not current_user.is_active:
        raise UnauthorizedError("Inactive user")
    return current_user
