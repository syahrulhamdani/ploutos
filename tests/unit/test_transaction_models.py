"""Unit tests for transaction models — schema, constraints, and relationships."""
from datetime import date, time
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ploutos.models.transaction import (
    Accounts,
    Cards,
    Currency,
    Institution,
    SubAccounts,
    TransactionCategory,
    Transactions,
)


async def _make_institution(session: AsyncSession, name: str) -> Institution:
    inst = Institution(name=name)
    session.add(inst)
    await session.commit()
    await session.refresh(inst)
    return inst


async def _make_account(
    session: AsyncSession, institution_id: int, account_number: str, owner: str = "Alice"
) -> Accounts:
    acct = Accounts(
        institution_id=institution_id,
        account_number=account_number,
        owner_name=owner,
    )
    session.add(acct)
    await session.commit()
    await session.refresh(acct)
    return acct


async def _make_sub_account(
    session: AsyncSession,
    account_id: int,
    name: str,
    currency: Currency = Currency.idr,
) -> SubAccounts:
    sub = SubAccounts(
        account_id=account_id,
        sub_account_name=name,
        sub_account_type="savings",
        currency=currency,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def _make_category(session: AsyncSession, name: str) -> TransactionCategory:
    cat = TransactionCategory(name=name)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def _make_transaction(
    session: AsyncSession,
    sub_account_id: int,
    category_id: UUID,
    *,
    trx_date: date = date(2024, 1, 1),
    amount: float = 100.0,
    direction: str = "in",
    counterparty_name: str = "Counterparty",
    **kwargs,
) -> Transactions:
    trx = Transactions(
        sub_account_id=sub_account_id,
        category_id=category_id,
        trx_date=trx_date,
        amount=amount,
        direction=direction,
        counterparty_name=counterparty_name,
        **kwargs,
    )
    session.add(trx)
    await session.commit()
    await session.refresh(trx)
    return trx


class TestInstitution:
    async def test_create(self, session: AsyncSession):
        inst = await _make_institution(session, "Bank Alpha")
        assert inst.institution_id is not None
        assert inst.name == "Bank Alpha"

    async def test_name_unique(self, session: AsyncSession):
        await _make_institution(session, "DuplicateBank")
        with pytest.raises(IntegrityError):
            await _make_institution(session, "DuplicateBank")


class TestAccounts:
    async def test_create_defaults(self, session: AsyncSession):
        inst = await _make_institution(session, "Bank Beta")
        acct = await _make_account(session, inst.institution_id, "ACC-BETA-001")
        assert acct.account_id is not None
        assert acct.is_active is True

    async def test_one_institution_many_accounts(self, session: AsyncSession):
        """An institution FK must not be unique — multiple accounts per institution."""
        inst = await _make_institution(session, "Bank Gamma")
        await _make_account(session, inst.institution_id, "ACC-G-001")
        await _make_account(session, inst.institution_id, "ACC-G-002")

        result = await session.exec(
            select(Accounts).where(Accounts.institution_id == inst.institution_id)
        )
        assert len(result.all()) == 2

    async def test_account_number_unique(self, session: AsyncSession):
        inst = await _make_institution(session, "Bank Delta")
        await _make_account(session, inst.institution_id, "SAME-ACCT")
        with pytest.raises(IntegrityError):
            await _make_account(session, inst.institution_id, "SAME-ACCT")


class TestSubAccounts:
    async def test_create_defaults(self, session: AsyncSession):
        inst = await _make_institution(session, "Bank Epsilon")
        acct = await _make_account(session, inst.institution_id, "ACC-EPS-001")
        sub = await _make_sub_account(session, acct.account_id, "Main Wallet")
        assert sub.sub_account_id is not None
        assert sub.currency == Currency.idr
        assert sub.is_active is True

    async def test_one_account_many_sub_accounts(self, session: AsyncSession):
        """account_id FK must not be unique — multiple sub-accounts per account."""
        inst = await _make_institution(session, "Bank Zeta")
        acct = await _make_account(session, inst.institution_id, "ACC-ZT-001")
        await _make_sub_account(session, acct.account_id, "SubZeta1", Currency.idr)
        await _make_sub_account(session, acct.account_id, "SubZeta2", Currency.usd)

        result = await session.exec(
            select(SubAccounts).where(SubAccounts.account_id == acct.account_id)
        )
        assert len(result.all()) == 2

    async def test_same_currency_on_multiple_sub_accounts(self, session: AsyncSession):
        """currency must not be unique — two sub-accounts may share the same currency."""
        inst = await _make_institution(session, "Bank Eta")
        acct = await _make_account(session, inst.institution_id, "ACC-ETA-001")
        await _make_sub_account(session, acct.account_id, "SubEta1", Currency.idr)


class TestCards:
    async def test_create(self, session: AsyncSession):
        inst = await _make_institution(session, "Bank Theta")
        acct = await _make_account(session, inst.institution_id, "ACC-TH-001")
        sub = await _make_sub_account(session, acct.account_id, "SubTheta")
        card = Cards(
            sub_account_id=sub.sub_account_id,
            card_number_masked="**** **** **** 1234",
            card_name="Alice Main",
        )
        session.add(card)
        await session.commit()
        await session.refresh(card)
        assert card.card_id is not None
        assert card.is_active is True

    async def test_card_number_unique(self, session: AsyncSession):
        inst = await _make_institution(session, "Bank Iota")
        acct = await _make_account(session, inst.institution_id, "ACC-IO-001")
        sub = await _make_sub_account(session, acct.account_id, "SubIota")

        session.add(Cards(sub_account_id=sub.sub_account_id, card_number_masked="**** 9999", card_name="X"))
        await session.commit()
        session.add(Cards(sub_account_id=sub.sub_account_id, card_number_masked="**** 9999", card_name="Y"))
        with pytest.raises(IntegrityError):
            await session.commit()


class TestTransactionCategory:
    async def test_create(self, session: AsyncSession):
        cat = await _make_category(session, "Food & Beverage")
        assert isinstance(cat.category_id, UUID)
        assert cat.name == "Food & Beverage"

    async def test_name_unique(self, session: AsyncSession):
        await _make_category(session, "Unique Category")
        with pytest.raises(IntegrityError):
            await _make_category(session, "Unique Category")


class TestTransactions:
    async def _scaffold(self, session: AsyncSession, tag: str):
        inst = await _make_institution(session, f"TrxBank{tag}")
        acct = await _make_account(session, inst.institution_id, f"TRX-{tag}")
        sub = await _make_sub_account(session, acct.account_id, f"TrxSub{tag}")
        cat = await _make_category(session, f"TrxCat{tag}")
        return sub, cat

    async def test_create_basic(self, session: AsyncSession):
        sub, cat = await self._scaffold(session, "A")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id)
        assert trx.transaction_id is not None
        assert trx.currency == Currency.idr

    async def test_one_sub_account_many_transactions(self, session: AsyncSession):
        """sub_account_id FK must not be unique — many transactions per sub-account."""
        sub, cat = await self._scaffold(session, "B")
        for i in range(3):
            await _make_transaction(
                session,
                sub.sub_account_id,
                cat.category_id,
                trx_date=date(2024, 2, i + 1),
                amount=1000.0 * (i + 1),
                direction="out",
                counterparty_name=f"Vendor {i}",
            )
        result = await session.exec(
            select(Transactions).where(Transactions.sub_account_id == sub.sub_account_id)
        )
        assert len(result.all()) == 3

    async def test_same_date_allowed_for_different_transactions(self, session: AsyncSession):
        """trx_date must not be unique — many transactions may share the same date."""
        sub, cat = await self._scaffold(session, "C")
        await _make_transaction(session, sub.sub_account_id, cat.category_id, trx_date=date(2024, 3, 1))
        await _make_transaction(session, sub.sub_account_id, cat.category_id, trx_date=date(2024, 3, 1))

    async def test_same_amount_allowed(self, session: AsyncSession):
        """amount must not be unique — many transactions may share the same amount."""
        sub, cat = await self._scaffold(session, "D")
        await _make_transaction(session, sub.sub_account_id, cat.category_id, amount=99.99)
        await _make_transaction(session, sub.sub_account_id, cat.category_id, amount=99.99)

    async def test_direction_invalid_value_rejected(self, session: AsyncSession):
        """direction must only accept 'in' or 'out'."""
        sub, cat = await self._scaffold(session, "E")
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 4, 1),
                amount=100.0,
                direction="sideways",
                counterparty_name="X",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    async def test_amount_negative_rejected(self, session: AsyncSession):
        """amount must be >= 0."""
        sub, cat = await self._scaffold(session, "F")
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 5, 1),
                amount=-500.0,
                direction="out",
                counterparty_name="X",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    async def test_optional_fields_accept_none(self, session: AsyncSession):
        """counterparty_ref, trx_reference_id, description, settlement_ref may all be None."""
        sub, cat = await self._scaffold(session, "G")
        trx = await _make_transaction(
            session,
            sub.sub_account_id,
            cat.category_id,
            counterparty_ref=None,
            trx_reference_id=None,
            description=None,
            settlement_ref=None,
        )
        assert trx.counterparty_ref is None
        assert trx.trx_reference_id is None
        assert trx.description is None

    async def test_trx_reference_id_unique(self, session: AsyncSession):
        """trx_reference_id must be unique when provided."""
        sub, cat = await self._scaffold(session, "H")
        ref = "REF-UNIQUE-001"
        await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            trx_date=date(2024, 7, 1), trx_reference_id=ref,
        )
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 7, 2),
                amount=200.0,
                direction="out",
                counterparty_name="B",
                trx_reference_id=ref,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    async def test_trx_time_optional(self, session: AsyncSession):
        """trx_time is optional and stored when provided."""
        sub, cat = await self._scaffold(session, "I")
        trx = await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            trx_time=time(14, 30, 0),
        )
        assert trx.trx_time is not None
