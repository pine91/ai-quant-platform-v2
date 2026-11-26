"""Persistent virtual accounts and idempotent simulated fills."""
import os
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import (
    BigInteger, Column, ForeignKey, MetaData, Numeric, String, Table,
    create_engine, insert, select, text, update,
)

metadata = MetaData()
accounts = Table(
    "paper_accounts", metadata,
    Column("instrument", String(100), primary_key=True),
    Column("cash", Numeric(28, 8), nullable=False),
    Column("units", Numeric(28, 8), nullable=False),
)
fills = Table(
    "paper_fills", metadata,
    Column("instrument", ForeignKey("paper_accounts.instrument"), primary_key=True),
    Column("request_id", String(36), primary_key=True),
    Column("side", String(4), nullable=False),
    Column("quantity", Numeric(28, 8), nullable=False),
    Column("price", Numeric(28, 8), nullable=False),
    Column("fee", Numeric(28, 8), nullable=False),
    Column("quote_time", BigInteger, nullable=False),
    Column("cash", Numeric(28, 8), nullable=False),
    Column("units", Numeric(28, 8), nullable=False),
)
QUANTUM = Decimal("0.00000001")


def database_url():
    return os.getenv("DATABASE_URL") or "sqlite:///paper.sqlite3"


@lru_cache
def engine(url):
    return create_engine(url, pool_pre_ping=True)


def initial_balance(currency):
    return Decimal("10000" if currency == "USD" else "10000000")


def portfolio(instrument, currency):
    with engine(database_url()).connect() as conn:
        account = conn.execute(select(accounts).where(accounts.c.instrument == instrument)).mappings().first()
        history = conn.execute(
            select(fills).where(fills.c.instrument == instrument).order_by(fills.c.quote_time, fills.c.request_id)
        ).mappings().all()
    return {"cash": account["cash"] if account else initial_balance(currency),
            "units": account["units"] if account else Decimal(0),
            "currency": currency, "fills": [dict(row) for row in history]}


def existing_paper_fill(instrument, request_id):
    with engine(database_url()).connect() as conn:
        row = conn.execute(select(fills).where(
            fills.c.instrument == instrument, fills.c.request_id == request_id
        )).mappings().first()
    return dict(row) if row else None


def paper_fill(instrument, currency, request_id, side, quantity, quote, fee_bps=10, slippage_bps=5):
    with engine(database_url()).begin() as conn:
        # The write acquires SQLite's writer lock. PostgreSQL locks the account row below.
        conn.execute(text(
            "INSERT INTO paper_accounts (instrument, cash, units) VALUES (:instrument, CAST(:cash AS NUMERIC), 0) "
            "ON CONFLICT (instrument) DO NOTHING"
        ), {"instrument": instrument, "cash": str(initial_balance(currency))})
        account_filter = accounts.c.instrument == instrument
        account = conn.execute(select(accounts).where(account_filter).with_for_update()).mappings().one()
        existing = conn.execute(select(fills).where(
            fills.c.instrument == instrument, fills.c.request_id == request_id
        )).mappings().first()
        if existing:
            if existing["side"] != side or existing["quantity"] != quantity:
                raise ValueError("Request ID was already used for a different fill")
            return dict(existing)
        if quote is None:
            raise LookupError("No candle available for simulated execution")
        sign = 1 if side == "buy" else -1
        price = (Decimal(str(quote["close"])) * (1 + sign * Decimal(slippage_bps) / 10_000)).quantize(QUANTUM)
        if price <= 0:
            raise LookupError("Invalid simulated execution price")
        gross = (quantity * price).quantize(QUANTUM)
        if gross <= 0:
            raise ValueError("Simulated fill is below the minimum monetary precision")
        fee = (gross * Decimal(fee_bps) / 10_000).quantize(QUANTUM)
        cash, units = account["cash"] - sign * gross - fee, account["units"] + sign * quantity
        if cash < 0 or units < 0:
            raise ValueError("Insufficient virtual balance or holdings")
        values = dict(instrument=instrument, request_id=request_id, side=side, quantity=quantity,
                      price=price, fee=fee, quote_time=quote["time"], cash=cash, units=units)
        conn.execute(update(accounts).where(account_filter).values(cash=cash, units=units))
        conn.execute(insert(fills).values(**values))
        return values
