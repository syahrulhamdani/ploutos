from datetime import date, time
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Date, Index, Time
from sqlmodel import Column, Field, Relationship, SQLModel


class Currency(str, Enum):
    idr = "IDR"
    usd = "USD"
    sgd = "SGD"


class Institution(SQLModel, table=True):
    __tablename__ = "institutions"

    institution_id: int | None = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, unique=True)

    accounts: list["Accounts"] = Relationship(back_populates="institution")


class Accounts(SQLModel, table=True):
    __tablename__ = "accounts"

    account_id: int | None = Field(default=None, primary_key=True)
    institution_id: int | None = Field(
        default=None, foreign_key="institutions.institution_id"
    )
    account_number: str = Field(nullable=False, unique=True)
    owner_name: str = Field(nullable=False)
    is_active: bool = Field(default=True)

    institution: Institution | None = Relationship(back_populates="accounts")
    sub_accounts: list["SubAccounts"] = Relationship(back_populates="account")


class SubAccounts(SQLModel, table=True):
    __tablename__ = "sub_accounts"

    sub_account_id: int | None = Field(default=None, primary_key=True)
    account_id: int | None = Field(
        default=None, nullable=False, foreign_key="accounts.account_id"
    )
    sub_account_name: str = Field(nullable=False, unique=True)
    sub_account_type: str = Field(nullable=False)
    currency: Currency = Field(default=Currency.idr, nullable=False)
    identifier: str | None = Field(default=None, nullable=True)
    is_active: bool = Field(default=True)

    account: Accounts | None = Relationship(back_populates="sub_accounts")
    cards: list["Cards"] = Relationship(back_populates="sub_account")
    transactions: list["Transactions"] = Relationship(back_populates="sub_account")


class Cards(SQLModel, table=True):
    __tablename__ = "cards"

    card_id: int | None = Field(default=None, primary_key=True)
    sub_account_id: int | None = Field(
        default=None, nullable=False, foreign_key="sub_accounts.sub_account_id"
    )
    card_number_masked: str = Field(nullable=False, unique=True)
    card_name: str = Field(nullable=False)
    is_active: bool = Field(default=True)

    sub_account: SubAccounts | None = Relationship(back_populates="cards")


class TransactionCategory(SQLModel, table=True):
    __tablename__ = "transaction_categories"

    category_id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False, unique=True)

    transactions: list["Transactions"] = Relationship(back_populates="category")


class Transactions(SQLModel, table=True):
    __tablename__ = "transactions"

    transaction_id: int | None = Field(default=None, primary_key=True)
    sub_account_id: int | None = Field(
        default=None, nullable=False, foreign_key="sub_accounts.sub_account_id"
    )
    category_id: UUID | None = Field(
        default=None, nullable=False, foreign_key="transaction_categories.category_id"
    )
    trx_date: date = Field(sa_column=Column(Date(), nullable=False))
    trx_time: time | None = Field(
        default=None,
        sa_column=Column(Time(timezone=True), nullable=True),
    )
    amount: float = Field(nullable=False)
    direction: str = Field(nullable=False)
    currency: Currency = Field(default=Currency.idr, nullable=False)
    counterparty_name: str = Field(nullable=False, description="Receiving party name")
    counterparty_ref: str | None = Field(
        default=None, nullable=True, description="Receiving party reference"
    )
    trx_reference_id: str | None = Field(
        default=None,
        nullable=True,
        description="Transaction reference id - unique per transaction",
        unique=True,
    )
    running_balance: float | None = Field(default=None, nullable=True)
    description: str | None = Field(default=None, nullable=True)
    settlement_ref: str | None = Field(
        default=None,
        nullable=True,
        description="Settlement reference, could be settlement uploaded URL",
    )

    sub_account: SubAccounts | None = Relationship(back_populates="transactions")
    category: TransactionCategory | None = Relationship(back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transactions_amount_non_negative"),
        CheckConstraint("direction IN ('in', 'out')", name="ck_transactions_direction"),
        Index("ix_trx_subaccount_date", "sub_account_id", "trx_date"),
        Index("ix_trx_category", "category_id"),
    )
