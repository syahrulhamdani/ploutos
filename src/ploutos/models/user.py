from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlmodel import Column, Field, SQLModel


class Role(str, Enum):
    admin = "admin"
    user = "user"
    viewer = "viewer"


class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    role: Role = Role.user
    is_active: bool = True


class User(UserBase, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class UserCreate(SQLModel):
    email: str
    password: str
    role: Role = Role.user


class UserRead(SQLModel):
    id: UUID
    email: str
    role: Role
    is_active: bool
    created_at: datetime
