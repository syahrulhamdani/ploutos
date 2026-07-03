from uuid import UUID

from ploutos.core.exceptions import AuthError, DuplicateError
from ploutos.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from ploutos.models.user import User, UserCreate, UserRead
from ploutos.repository.user import UserRepository
from ploutos.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def register(self, user_create: UserCreate) -> UserRead:
        existing = await self._user_repo.get_by_email(user_create.email)
        if existing:
            raise DuplicateError(f"Email '{user_create.email}' is already registered")

        hashed = hash_password(user_create.password)
        user = await self._user_repo.create(user_create, hashed)
        return UserRead.model_validate(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("Account is inactive")
        return self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self._user_repo.get_by_id(UUID(payload.sub))
        if not user or not user.is_active:
            raise AuthError("User not found or inactive")
        return self._issue_tokens(user)

    def _issue_tokens(self, user: User) -> TokenResponse:
        token_data = {"sub": str(user.id), "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
