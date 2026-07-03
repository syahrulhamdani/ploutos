import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from ploutos.core.config import settings
from ploutos.core.database import get_session
from ploutos.main import create_app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Override JWT secret to meet the 32-byte minimum recommended by RFC 7518
settings.JWT_SECRET_KEY = "test-secret-key-that-is-long-enough-32b"


@pytest_asyncio.fixture(scope="session")
async def engine():
    _engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield _engine
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await _engine.dispose()


@pytest_asyncio.fixture()
async def session(engine):
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest_asyncio.fixture()
async def client(session):
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
