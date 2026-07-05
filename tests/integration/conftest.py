"""Integration test fixtures backed by the real PostgreSQL database."""
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ploutos.core.config import settings

DATABASE_URL = os.environ.get("DATABASE_URL", settings.DATABASE_URL)


@pytest.fixture(scope="session")
def pg_engine():
    import asyncio

    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

    async def _teardown():
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_setup())
    yield engine
    asyncio.run(_teardown())


@pytest_asyncio.fixture()
async def session(pg_engine):
    factory = sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
        try:
            await s.rollback()
        except Exception:
            pass
