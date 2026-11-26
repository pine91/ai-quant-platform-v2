"""Read-only historical candle adapters. No order execution."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import httpx
from .markets import Market, Instrument
from .timeframes import Timeframe, DEFAULT_TIMEFRAME, BITHUMB_MINUTES, YAHOO_INTERVALS, YAHOO_RANGES

async def candles(instrument: Instrument, timeframe: Timeframe = DEFAULT_TIMEFRAME, session: str = "regular"):
    if session not in ("regular", "pre", "post"):
        raise ValueError("Invalid session")
    if session != "regular" and (instrument.market != Market.US_STOCK or timeframe in (Timeframe.D1, Timeframe.W1, Timeframe.H4, Timeframe.H1)):
        raise ValueError("Extended sessions currently support US stock minute candles only")
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
        aggregate = timeframe == Timeframe.H4
        if aggregate:
            timeframe = Timeframe.H1
        response = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/" + symbol,
            params={"range": YAHOO_RANGES[timeframe.value], "interval": YAHOO_INTERVALS[timeframe.value], "includePrePost": str(session != "regular").lower()}, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        result = response.json()["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        rows = [{"time": t, **{k: quote[k][i] for k in ("open","high","low","close")}}
                for i,t in enumerate(result["timestamp"])
                if all(quote[k][i] is not None for k in ("open","high","low","close"))]

        if session != "regular":
            zone = ZoneInfo("America/New_York")
            start, end = (240, 570) if session == "pre" else (960, 1200)
            rows = [r for r in rows if start <= (lambda d: d.hour * 60 + d.minute)(datetime.fromtimestamp(r["time"], zone)) < end]
        if not aggregate:
            return rows
        zone = ZoneInfo("Asia/Seoul" if instrument.market == Market.KR_STOCK else "America/New_York")
        start = 540 if instrument.market == Market.KR_STOCK else 570
        groups = {}
        for row in sorted(rows, key=lambda r: r["time"]):
            local = datetime.fromtimestamp(row["time"], zone)
            offset = local.hour * 60 + local.minute - start
            if not 0 <= offset < 390:
                continue
            key = (local.date(), offset // 240)
            if key not in groups:
                groups[key] = dict(row)
            else:
                bar = groups[key]
                bar["high"] = max(bar["high"], row["high"])
                bar["low"] = min(bar["low"], row["low"])
                bar["close"] = row["close"]
        return list(groups.values())
