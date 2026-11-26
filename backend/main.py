import json
import os
from decimal import Decimal
from uuid import UUID
from typing import Annotated, Literal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

import httpx
from dotenv import load_dotenv

from .analysis import analyze_chart
from .cache import cached_candles
from .indicators import indicators
from .kis import kis_candles
from .market_data import ProviderError, candles, validated_candles
from .markets import Instrument, Market
from .overnight import overnight_candles
from .simulation import backtest
from .storage import existing_paper_fill, paper_fill, portfolio
from .timeframes import DEFAULT_TIMEFRAME, Timeframe

load_dotenv()

app = FastAPI(title="AI Quant Platform V2", version="0.1.0")


class HealthResponse(BaseModel):
    status: str


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.get("/api/markets/{market}/candles")
async def market_candles(market: Market, symbol: Annotated[str, Query(min_length=1, max_length=32)], timeframe: Timeframe = DEFAULT_TIMEFRAME, session: Literal["regular", "pre", "post", "overnight"] = "regular", venue: Literal["krx", "nxt"] | None = None):
    try:
        instrument = Instrument(market=market, symbol=symbol)
        if venue:
            if market != Market.KR_STOCK or session != "regular":
                raise ValueError("KIS venue selection is for Korean stocks only")
            try:
                rows = await kis_candles(symbol, timeframe, venue)
            except RuntimeError as exc:
                raise HTTPException(503, "KIS quotes not configured") from exc
        elif session == "overnight":
            if os.getenv("ENABLE_OVERNIGHT", "false").lower() != "true":
                raise HTTPException(status_code=503, detail="Overnight trading data is disabled")
            if market != Market.US_STOCK:
                raise ValueError("Overnight is US stock only")
            rows = await overnight_candles(symbol, timeframe.value)
        else:
            cache_key = "quant-v2:candles:" + json.dumps([market.value, symbol.upper(), timeframe.value, session])
            rows = await cached_candles(cache_key, lambda: candles(instrument, timeframe, session=session))
        rows = validated_candles(rows)
        return {"market": market, "symbol": symbol, "currency": instrument.currency,
                "interval": timeframe.value, "session": session, "venue": venue, "candles": rows, "indicators": indicators(rows)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Market data provider not configured") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid symbol or market data") from exc
    except (ProviderError, httpx.HTTPError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail="Market data provider unavailable") from exc


@app.post("/api/markets/{market}/analysis")
async def market_analysis(
    market: Market, symbol: str, timeframe: Timeframe = DEFAULT_TIMEFRAME,
    session: Literal["regular", "pre", "post", "overnight"] = "regular",
    venue: Literal["krx", "nxt"] | None = None,
):
    return await analyze_chart(lambda: market_candles(market, symbol, timeframe, session, venue))


@app.get("/api/markets/{market}/backtest")
async def market_backtest(
    market: Market, symbol: str, timeframe: Timeframe = DEFAULT_TIMEFRAME,
    session: Literal["regular", "pre", "post", "overnight"] = "regular",
    venue: Literal["krx", "nxt"] | None = None,
    initial_cash: Annotated[float, Query(gt=0, le=1e12)] = 10000,
    fee_bps: Annotated[float, Query(ge=0, le=1000)] = 10,
    slippage_bps: Annotated[float, Query(ge=0, le=1000)] = 5,
):
    snapshot = await market_candles(market, symbol, timeframe, session, venue)
    return {**backtest(snapshot["candles"], initial_cash, fee_bps, slippage_bps),
            "currency": snapshot["currency"]}


class PaperOrder(BaseModel):
    request_id: UUID
    side: Literal["buy", "sell"]
    quantity: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=8)]


def paper_instrument(market, symbol, venue):
    symbol = symbol.strip().upper()
    if venue:
        if market != Market.KR_STOCK:
            raise HTTPException(422, "Venue selection is for Korean stocks only")
        symbol = symbol.split(".")[0]
    elif market == Market.KR_STOCK and len(symbol) == 6 and symbol.isdigit():
        symbol += ".KS"
    elif market == Market.CRYPTO and symbol.endswith("-KRW"):
        symbol = "KRW-" + symbol[:-4]
    instrument = Instrument(market=market, symbol=symbol)
    return f"{market.value}:{venue or 'default'}:{instrument.symbol}", instrument.currency


@app.get("/api/markets/{market}/paper")
def paper_portfolio(
    market: Market, symbol: Annotated[str, Query(min_length=1, max_length=32)],
    venue: Literal["krx", "nxt"] | None = None,
):
    try:
        return portfolio(*paper_instrument(market, symbol, venue))
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Paper database unavailable. Run database migrations.") from exc
    except ValueError as exc:
        raise HTTPException(422, "Invalid paper instrument") from exc


@app.post("/api/markets/{market}/paper")
async def place_paper_order(
    order: PaperOrder, market: Market, symbol: Annotated[str, Query(min_length=1, max_length=32)],
    timeframe: Timeframe = DEFAULT_TIMEFRAME,
    session: Literal["regular", "pre", "post", "overnight"] = "regular",
    venue: Literal["krx", "nxt"] | None = None,
):
    try:
        instrument, currency = paper_instrument(market, symbol, venue)
        existing = await run_in_threadpool(existing_paper_fill, instrument, str(order.request_id))
        quote = None
        if existing is None:
            snapshot = await market_candles(market, symbol, timeframe, session, venue)
            quote = snapshot["candles"][-1] if snapshot["candles"] else None
        return await run_in_threadpool(
            paper_fill, instrument, currency, str(order.request_id), order.side, order.quantity, quote
        )
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Paper database unavailable. Run database migrations.") from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
