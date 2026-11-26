import os
from datetime import datetime, timedelta, timezone
import httpx

from .market_data import provider_json

async def overnight_candles(symbol: str, timeframe: str):
    intervals = {"1m":"1Min","5m":"5Min","15m":"15Min","30m":"30Min","1h":"1Hour","4h":"4Hour"}
    if timeframe not in intervals:
        raise ValueError("Overnight supports intraday intervals only")
    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        raise RuntimeError("Alpaca credentials not configured")
    end = datetime.now(timezone.utc) - timedelta(minutes=15)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get("https://data.alpaca.markets/v2/stocks/bars", headers={"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret}, params={"symbols":symbol.upper(),"timeframe":intervals[timeframe],"feed":"boats","start":(end-timedelta(days=7)).isoformat(),"end":end.isoformat(),"limit":1000})
        bars = provider_json(response).get("bars", {}).get(symbol.upper(), [])
        return [{"time":int(datetime.fromisoformat(b["t"].replace("Z","+00:00")).timestamp()),"open":b["o"],"high":b["h"],"low":b["l"],"close":b["c"],"volume":b["v"]} for b in bars]
