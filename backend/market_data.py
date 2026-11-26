"""Read-only historical candle adapters. No order execution."""
from datetime import datetime, timezone
import httpx
from .markets import Market, Instrument
from .timeframes import Timeframe, DEFAULT_TIMEFRAME, BITHUMB_MINUTES, YAHOO_INTERVALS, YAHOO_RANGES

async def candles(instrument: Instrument, timeframe: Timeframe = DEFAULT_TIMEFRAME):
    async with httpx.AsyncClient(timeout=15) as client:
        if instrument.market == Market.CRYPTO:
            symbol = instrument.symbol.upper()
            if symbol.endswith("-KRW"):
                symbol = "KRW-" + symbol[:-4]
            path = ("days" if timeframe == Timeframe.D1 else "weeks" if timeframe == Timeframe.W1 else f"minutes/{BITHUMB_MINUTES[timeframe.value]}")
            response = await client.get("https://api.bithumb.com/v1/candles/" + path, params={"market": symbol, "count": 100})
            response.raise_for_status()
            rows = response.json()
            return sorted([{
                "time": int(datetime.fromisoformat(r["candle_date_time_utc"]).replace(tzinfo=timezone.utc).timestamp()),
                "open": r["opening_price"], "high": r["high_price"],
                "low": r["low_price"], "close": r["trade_price"]
            } for r in rows], key=lambda r: r["time"])
        symbol = instrument.symbol.upper()
        if instrument.market == Market.KR_STOCK:
            if len(symbol) == 6 and symbol.isdigit():
                symbol += ".KS"
            elif not (len(symbol) == 9 and symbol[:6].isdigit() and symbol[6:] in (".KS", ".KQ")):
                raise ValueError("Expected six-digit code with optional .KS (KOSPI) or .KQ (KOSDAQ)")
        elif not symbol.replace("-", "").replace(".", "").isalnum():
            raise ValueError("Invalid stock symbol")
        if timeframe == Timeframe.H4:
            raise ValueError("Stock 4h candles require session-aware aggregation")
        response = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol,
            params={"range": YAHOO_RANGES[timeframe.value], "interval": YAHOO_INTERVALS[timeframe.value]}, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        return [{"time": t, **{k: quote[k][i] for k in ("open","high","low","close")}}
                for i,t in enumerate(result["timestamp"])
                if all(quote[k][i] is not None for k in ("open","high","low","close"))]
