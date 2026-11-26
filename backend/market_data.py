"""Read-only historical candle adapters. No order execution."""
from datetime import datetime, timezone
import httpx
from .markets import Market, Instrument

async def candles(instrument: Instrument):
    async with httpx.AsyncClient(timeout=15) as client:
        if instrument.market == Market.CRYPTO:
            symbol = instrument.symbol.upper()
            if symbol.endswith("-KRW"):
                symbol = "KRW-" + symbol[:-4]
            response = await client.get("https://api.bithumb.com/v1/candles/days", params={"market": symbol, "count": 100})
            response.raise_for_status()
            rows = response.json()
            return sorted([{
                "time": int(datetime.fromisoformat(r["candle_date_time_utc"]).replace(tzinfo=timezone.utc).timestamp()),
                "open": r["opening_price"], "high": r["high_price"],
                "low": r["low_price"], "close": r["trade_price"]
            } for r in rows], key=lambda r: r["time"])
        symbol = instrument.symbol.upper()
        if instrument.market == Market.KR_STOCK:
            if not (len(symbol) == 6 and symbol.isdigit()):
                raise ValueError("Expected a six-digit Korean stock code")
            # Initial support for KOSPI; KOSDAQ mapping will be added separately.
            symbol += ".KS"
        elif not symbol.replace("-", "").replace(".", "").isalnum():
            raise ValueError("Invalid stock symbol")
        response = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol,
            params={"range": "6mo", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        return [{"time": t, **{k: quote[k][i] for k in ("open","high","low","close")}}
                for i,t in enumerate(result["timestamp"])
                if all(quote[k][i] is not None for k in ("open","high","low","close"))]
