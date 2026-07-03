from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from ploutos.core.database import get_session
from ploutos.core.dependencies import get_current_user, require_role
from ploutos.models.user import Role, UserCreate, UserRead
from ploutos.repository.user import UserRepository
from ploutos.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from ploutos.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session))


@router.post("/register", response_model=UserRead, status_code=201)
async def register(
    user_create: UserCreate,
    service: AuthService = Depends(_auth_service),
) -> UserRead:
    return await service.register(user_create)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    service: AuthService = Depends(_auth_service),
) -> TokenResponse:
    return await service.login(body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(_auth_service),
) -> TokenResponse:
    return await service.refresh(body.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    return current_user


@router.get("/admin", dependencies=[Depends(require_role(Role.admin))])
async def admin_only() -> dict:
    return {"message": "welcome, admin"}
