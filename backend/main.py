from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AI Quant Platform V2", version="0.1.0")

class HealthResponse(BaseModel):
    status: str

@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")

from fastapi import HTTPException
import httpx
from .markets import Market, Instrument
from .market_data import candles
from .overnight import overnight_candles
from .timeframes import Timeframe, DEFAULT_TIMEFRAME

@app.get("/api/markets/{market}/candles")
async def market_candles(market: Market, symbol: str, timeframe: Timeframe = DEFAULT_TIMEFRAME, session: Literal["regular", "pre", "post", "overnight"] = "regular"):
    try:
        instrument = Instrument(market=market, symbol=symbol)
        if session == "overnight":
            if market != Market.US_STOCK:
                raise ValueError("Overnight is US stock only")
            rows = await overnight_candles(symbol, timeframe.value)
        else:
            rows = await candles(instrument, timeframe, session=session)
        return {"market": market, "symbol": symbol, "currency": instrument.currency,
                "interval": timeframe.value, "session": session, "candles": rows}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Market data provider not configured") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid symbol or market data") from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Market data provider unavailable") from exc
