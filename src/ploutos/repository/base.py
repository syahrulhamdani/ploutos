from typing import Generic, TypeVar
from uuid import UUID

from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: UUID) -> ModelT | None:
        return await self.session.get(self.model, id)

    async def list(self) -> list[ModelT]:
        result = await self.session.exec(select(self.model))
        return list(result.all())

    async def save(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.commit()
