from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ploutos.core.database import get_session
from ploutos.core.exceptions import AuthError, PermissionDeniedError
from ploutos.core.security import decode_token
from ploutos.models.user import Role, User, UserRead
from ploutos.repository.user import UserRepository
from sqlmodel.ext.asyncio.session import AsyncSession

_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    payload = decode_token(credentials.credentials, expected_type="access")
    repo = UserRepository(session)
    user: User | None = await repo.get_by_id(UUID(payload.sub))
    if not user or not user.is_active:
        raise AuthError("User not found or inactive")
    return UserRead.model_validate(user)


def require_role(*roles: Role) -> Callable:
    async def dependency(current_user: UserRead = Depends(get_current_user)) -> UserRead:
        if current_user.role not in roles:
            raise PermissionDeniedError(
                f"Required role(s): {[r.value for r in roles]}"
            )
        return current_user

    return dependency
