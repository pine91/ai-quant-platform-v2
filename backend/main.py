import os
from typing import Annotated, Literal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="AI Quant Platform V2", version="0.1.0")

class HealthResponse(BaseModel):
    status: str

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")

import httpx
from .markets import Market, Instrument
from .market_data import ProviderError, candles
from .overnight import overnight_candles
from .kis import kis_candles
from .indicators import indicators
from .analysis import analyze_chart
from .simulation import backtest
from .timeframes import Timeframe, DEFAULT_TIMEFRAME

@app.get("/api/markets/{market}/candles")
async def market_candles(market: Market, symbol: str, timeframe: Timeframe = DEFAULT_TIMEFRAME, session: Literal["regular", "pre", "post", "overnight"] = "regular", venue: Literal["krx", "nxt"] | None = None):
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
            rows = await candles(instrument, timeframe, session=session)
        return {"market": market, "symbol": symbol, "currency": instrument.currency,
                "interval": timeframe.value, "session": session, "venue": venue, "candles": rows, "indicators": indicators(rows)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Market data provider not configured") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid symbol or market data") from exc
    except (ProviderError, httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
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
    if any(min(bar["open"], bar["close"]) <= 0 for bar in snapshot["candles"]):
        raise HTTPException(502, "Invalid execution prices")
    return {**backtest(snapshot["candles"], initial_cash, fee_bps, slippage_bps),
            "currency": snapshot["currency"]}
