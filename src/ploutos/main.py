from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from ploutos.api.v1.router import router
from ploutos.core.database import init_db
from ploutos.core.exceptions import register_exception_handlers
from ploutos.core.loggers import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    await init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ploutos", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(router)

    @app.get("/health", tags=["health"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
