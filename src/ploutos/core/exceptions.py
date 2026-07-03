from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AuthError(Exception):
    def __init__(self, detail: str = "Authentication failed") -> None:
        self.detail = detail
        super().__init__(detail)


class PermissionDeniedError(Exception):
    def __init__(self, detail: str = "Permission denied") -> None:
        self.detail = detail
        super().__init__(detail)


class NotFoundError(Exception):
    def __init__(self, detail: str = "Resource not found") -> None:
        self.detail = detail
        super().__init__(detail)


class DuplicateError(Exception):
    def __init__(self, detail: str = "Resource already exists") -> None:
        self.detail = detail
        super().__init__(detail)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": exc.detail})

    @app.exception_handler(PermissionDeniedError)
    async def permission_error_handler(
        request: Request, exc: PermissionDeniedError
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": exc.detail})

    @app.exception_handler(NotFoundError)
    async def not_found_handler(
        request: Request, exc: NotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": exc.detail})

    @app.exception_handler(DuplicateError)
    async def duplicate_handler(
        request: Request, exc: DuplicateError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": exc.detail})
