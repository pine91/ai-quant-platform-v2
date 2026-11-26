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
from .timeframes import Timeframe, DEFAULT_TIMEFRAME

@app.get("/api/markets/{market}/candles")
async def market_candles(market: Market, symbol: str, timeframe: Timeframe = DEFAULT_TIMEFRAME, session: Literal["regular", "pre", "post", "overnight"] = "regular"):
    if session == "overnight":
        raise HTTPException(status_code=501, detail="Overnight market data provider not configured")
    try:
        instrument = Instrument(market=market, symbol=symbol)
        rows = await candles(instrument, timeframe, session=session)
        return {"market": market, "symbol": symbol, "currency": instrument.currency,
                "interval": timeframe.value, "session": session, "candles": rows}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid symbol or market data") from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Market data provider unavailable") from exc
