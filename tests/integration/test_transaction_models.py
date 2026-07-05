"""Integration tests for transaction models against a real PostgreSQL database.

Run with:
    uv run --env-file .env.claude pytest -v tests/integration/test_transaction_models.py
"""
from datetime import date, time, timezone
from uuid import UUID, uuid4

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_institution(session: AsyncSession, name: str) -> Institution:
    inst = Institution(name=name)
    session.add(inst)
    await session.commit()
    await session.refresh(inst)
    return inst


async def _make_account(
    session: AsyncSession,
    institution_id: int,
    account_number: str,
    owner: str = "Alice",
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


async def _scaffold(session: AsyncSession, tag: str):
    """Return a (SubAccounts, TransactionCategory) pair for test use."""
    inst = await _make_institution(session, f"IntgBank{tag}")
    acct = await _make_account(session, inst.institution_id, f"INTG-{tag}")
    sub = await _make_sub_account(session, acct.account_id, f"IntgSub{tag}")
    cat = await _make_category(session, f"IntgCat{tag}")
    return sub, cat


# ---------------------------------------------------------------------------
# FK integrity — PostgreSQL enforces these; SQLite does not
# ---------------------------------------------------------------------------


class TestForeignKeyIntegrity:
    async def test_account_with_nonexistent_institution_rejected(self, session: AsyncSession):
        session.add(Accounts(institution_id=999999, account_number="FK-TEST-1", owner_name="X"))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_sub_account_with_nonexistent_account_rejected(self, session: AsyncSession):
        session.add(
            SubAccounts(
                account_id=999999,
                sub_account_name="OrphanSub",
                sub_account_type="savings",
                currency=Currency.idr,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_transaction_with_nonexistent_sub_account_rejected(self, session: AsyncSession):
        inst = await _make_institution(session, "FKBank1")
        await _make_account(session, inst.institution_id, "FK-ACCT-1")
        cat = await _make_category(session, "FKCat1")
        session.add(
            Transactions(
                sub_account_id=999999,
                category_id=cat.category_id,
                trx_date=date(2024, 1, 1),
                amount=100.0,
                direction="in",
                counterparty_name="X",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_transaction_with_nonexistent_category_rejected(self, session: AsyncSession):
        sub, _ = await _scaffold(session, "FK2")
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=uuid4(),
                trx_date=date(2024, 1, 1),
                amount=100.0,
                direction="in",
                counterparty_name="X",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


# ---------------------------------------------------------------------------
# CHECK constraints — enforced at PostgreSQL level
# ---------------------------------------------------------------------------


class TestCheckConstraints:
    async def test_negative_amount_rejected(self, session: AsyncSession):
        sub, cat = await _scaffold(session, "CHK1")
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 1, 1),
                amount=-0.01,
                direction="out",
                counterparty_name="X",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_zero_amount_allowed(self, session: AsyncSession):
        """Boundary value: zero amount represents a waived fee or no-cost receipt."""
        sub, cat = await _scaffold(session, "CHK2")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id, amount=0.0)
        assert trx.transaction_id is not None

    async def test_invalid_direction_rejected(self, session: AsyncSession):
        sub, cat = await _scaffold(session, "CHK3")
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 1, 1),
                amount=50.0,
                direction="transfer",
                counterparty_name="X",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_direction_in_allowed(self, session: AsyncSession):
        sub, cat = await _scaffold(session, "CHK4")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id, direction="in")
        assert trx.direction == "in"

    async def test_direction_out_allowed(self, session: AsyncSession):
        sub, cat = await _scaffold(session, "CHK5")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id, direction="out")
        assert trx.direction == "out"


# ---------------------------------------------------------------------------
# Unique constraints
# ---------------------------------------------------------------------------


class TestUniqueConstraints:
    async def test_duplicate_institution_name_rejected(self, session: AsyncSession):
        await _make_institution(session, "UniqInst")
        with pytest.raises(IntegrityError):
            await _make_institution(session, "UniqInst")
        await session.rollback()

    async def test_duplicate_account_number_rejected(self, session: AsyncSession):
        inst = await _make_institution(session, "UniqAcctBank")
        await _make_account(session, inst.institution_id, "UNIQ-ACCT-001")
        with pytest.raises(IntegrityError):
            await _make_account(session, inst.institution_id, "UNIQ-ACCT-001")
        await session.rollback()

    async def test_duplicate_sub_account_name_rejected(self, session: AsyncSession):
        inst = await _make_institution(session, "UniqSubBank")
        acct = await _make_account(session, inst.institution_id, "UNIQ-SUB-001")
        await _make_sub_account(session, acct.account_id, "SameName", Currency.idr)
        with pytest.raises(IntegrityError):
            await _make_sub_account(session, acct.account_id, "SameName", Currency.usd)
        await session.rollback()

    async def test_duplicate_card_number_rejected(self, session: AsyncSession):
        inst = await _make_institution(session, "UniqCardBank")
        acct = await _make_account(session, inst.institution_id, "UNIQ-CARD-001")
        sub = await _make_sub_account(session, acct.account_id, "UniqCardSub")
        session.add(Cards(sub_account_id=sub.sub_account_id, card_number_masked="**** 1111", card_name="A"))
        await session.commit()
        session.add(Cards(sub_account_id=sub.sub_account_id, card_number_masked="**** 1111", card_name="B"))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_duplicate_category_name_rejected(self, session: AsyncSession):
        await _make_category(session, "UniqCatName")
        with pytest.raises(IntegrityError):
            await _make_category(session, "UniqCatName")
        await session.rollback()

    async def test_duplicate_trx_reference_id_rejected(self, session: AsyncSession):
        sub, cat = await _scaffold(session, "UNIQREF")
        ref = "TXN-REF-UNIQUE-999"
        await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            trx_date=date(2024, 6, 1), trx_reference_id=ref,
        )
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 6, 2),
                amount=50.0,
                direction="out",
                counterparty_name="Y",
                trx_reference_id=ref,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_null_trx_reference_id_allowed_on_multiple_rows(self, session: AsyncSession):
        """NULL is not subject to the unique constraint — common for receipt imports."""
        sub, cat = await _scaffold(session, "NULLREF")
        for i in range(3):
            await _make_transaction(
                session, sub.sub_account_id, cat.category_id,
                trx_date=date(2024, 7, i + 1),
                trx_reference_id=None,
            )


# ---------------------------------------------------------------------------
# LLM-extraction edge cases
# ---------------------------------------------------------------------------


class TestLLMExtractionEdgeCases:
    async def test_bulk_statement_import_same_date(self, session: AsyncSession):
        """Simulates a monthly statement: many transactions on the same date."""
        sub, cat = await _scaffold(session, "BULK")
        for i in range(15):
            await _make_transaction(
                session, sub.sub_account_id, cat.category_id,
                trx_date=date(2024, 3, 15),
                amount=float(1000 + i * 250),
                direction="out" if i % 2 == 0 else "in",
                counterparty_name=f"Merchant {i}",
                trx_reference_id=f"STMT-REF-{i:04d}",
            )
        result = await session.exec(
            select(Transactions).where(Transactions.sub_account_id == sub.sub_account_id)
        )
        assert len(result.all()) == 15

    async def test_duplicate_extraction_rejected_via_reference_id(self, session: AsyncSession):
        """LLM extracts the same transaction twice; second insert must be rejected."""
        sub, cat = await _scaffold(session, "DUPEXT")
        ref = "BANK-REF-20240401-001"
        await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            trx_date=date(2024, 4, 1), trx_reference_id=ref,
        )
        session.add(
            Transactions(
                sub_account_id=sub.sub_account_id,
                category_id=cat.category_id,
                trx_date=date(2024, 4, 1),
                amount=100.0,
                direction="in",
                counterparty_name="Same Payer",
                trx_reference_id=ref,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async def test_all_optional_fields_none(self, session: AsyncSession):
        """LLM may return None for all optional fields (e.g. scanned receipt with no ref)."""
        sub, cat = await _scaffold(session, "ALLNONE")
        trx = await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            counterparty_ref=None,
            trx_reference_id=None,
            running_balance=None,
            description=None,
            settlement_ref=None,
        )
        assert trx.transaction_id is not None
        assert trx.counterparty_ref is None
        assert trx.description is None

    async def test_multi_currency_sub_accounts_on_same_account(self, session: AsyncSession):
        """LLM extracts from a multi-currency account; sub-accounts share the same account."""
        inst = await _make_institution(session, "MultiCurrBank")
        acct = await _make_account(session, inst.institution_id, "MULTI-CURR-001")
        sub_idr = await _make_sub_account(session, acct.account_id, "IDR Wallet", Currency.idr)
        sub_usd = await _make_sub_account(session, acct.account_id, "USD Wallet", Currency.usd)
        sub_sgd = await _make_sub_account(session, acct.account_id, "SGD Wallet", Currency.sgd)
        assert sub_idr.currency == Currency.idr
        assert sub_usd.currency == Currency.usd
        assert sub_sgd.currency == Currency.sgd

    async def test_zero_amount_receipt(self, session: AsyncSession):
        """Receipts for waived fees or free transactions have amount=0."""
        sub, cat = await _scaffold(session, "ZEROFEE")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id, amount=0.0)
        assert trx.amount == 0.0

    async def test_statement_import_without_time(self, session: AsyncSession):
        """Daily/monthly statements rarely include time; trx_time should be omitted."""
        sub, cat = await _scaffold(session, "NOTIME")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id, trx_time=None)
        assert trx.trx_time is None

    async def test_receipt_with_exact_time(self, session: AsyncSession):
        """Individual receipts or e-wallet exports include a timestamp."""
        sub, cat = await _scaffold(session, "WITHTIME")
        trx = await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            trx_time=time(9, 45, 30, tzinfo=timezone.utc),
        )
        assert trx.trx_time is not None

    async def test_running_balance_tracked(self, session: AsyncSession):
        """Statements from some banks include a running balance per row."""
        sub, cat = await _scaffold(session, "RUNBAL")
        trx = await _make_transaction(
            session, sub.sub_account_id, cat.category_id,
            amount=500_000.0,
            direction="in",
            running_balance=2_500_000.0,
        )
        assert trx.running_balance == 2_500_000.0


# ---------------------------------------------------------------------------
# Relationship traversal
# ---------------------------------------------------------------------------


class TestRelationshipTraversal:
    async def test_institution_to_transaction_chain(self, session: AsyncSession):
        """Verify the full Institution → Account → SubAccount → Transaction chain is accessible."""
        inst = await _make_institution(session, "ChainBank")
        acct = await _make_account(session, inst.institution_id, "CHAIN-001")
        sub = await _make_sub_account(session, acct.account_id, "ChainSub")
        cat = await _make_category(session, "ChainCat")
        trx = await _make_transaction(session, sub.sub_account_id, cat.category_id)

        fetched_trx = await session.get(Transactions, trx.transaction_id)
        assert fetched_trx is not None

        fetched_sub = await session.get(SubAccounts, fetched_trx.sub_account_id)
        assert fetched_sub.account_id == acct.account_id

        fetched_acct = await session.get(Accounts, fetched_sub.account_id)
        assert fetched_acct.institution_id == inst.institution_id

    async def test_category_uuid_pk_persisted_correctly(self, session: AsyncSession):
        """TransactionCategory uses a UUID PK; verify it round-trips through PostgreSQL."""
        cat = await _make_category(session, "UUIDCheck")
        assert isinstance(cat.category_id, UUID)

        fetched = await session.get(TransactionCategory, cat.category_id)
        assert fetched is not None
        assert fetched.category_id == cat.category_id
