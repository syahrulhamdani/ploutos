from uuid import UUID

from sqlmodel import select

from ploutos.models.user import User, UserCreate
from ploutos.repository.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.exec(select(User).where(User.email == email))
        return result.first()

    async def get_by_id(self, id: UUID) -> User | None:
        return await self.session.get(User, id)

    async def create(self, data: UserCreate, hashed_password: str) -> User:
        user = User(
            email=data.email,
            hashed_password=hashed_password,
            role=data.role,
        )
        return await self.save(user)
