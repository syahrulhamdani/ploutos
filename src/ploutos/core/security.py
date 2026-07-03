from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ploutos.core.config import settings
from ploutos.core.exceptions import AuthError
from ploutos.schemas.auth import TokenPayload


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    return jwt.encode(
        {**data, "exp": expire, "type": "access"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    return jwt.encode(
        {**data, "exp": expire, "type": "refresh"},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")

    if payload.get("type") != expected_type:
        raise AuthError("Invalid token type")

    return TokenPayload(sub=payload["sub"], role=payload["role"], exp=payload["exp"])
