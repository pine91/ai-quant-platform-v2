"""Korea Investment & Securities venue-specific historical quotes."""
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from .market_data import ProviderError
from .timeframes import Timeframe

BASE = "https://openapi.koreainvestment.com:9443"


async def kis_candles(symbol: str, timeframe: Timeframe, venue: str):
    if not re.fullmatch(r"[0-9]{6}(?:\.(?:KS|KQ))?", symbol.upper()):
        raise ValueError("Invalid Korean stock code")
    key = os.getenv("KIS_APP_KEY")
    secret = os.getenv("KIS_APP_SECRET")
    token = os.getenv("KIS_ACCESS_TOKEN")
    if not all((key, secret, token)):
        raise RuntimeError("KIS quote credentials missing")
    if timeframe not in (Timeframe.M1, Timeframe.D1, Timeframe.W1):
        raise ValueError("KIS supports 1m, 1d and 1w")
    zone = ZoneInfo("Asia/Seoul")
    now = datetime.now(zone)
    intraday = timeframe == Timeframe.M1
    params = {"FID_COND_MRKT_DIV_CODE": {"krx": "J", "nxt": "NX"}[venue],
              "FID_INPUT_ISCD": symbol[:6]}
    if intraday:
        path, tr_id = "inquire-time-itemchartprice", "FHKST03010200"
        params.update(FID_INPUT_HOUR_1=min(now.strftime("%H%M%S"), "200000"),
                      FID_PW_DATA_INCU_YN="N", FID_ETC_CLS_CODE="")
    else:
        path, tr_id = "inquire-daily-itemchartprice", "FHKST03010100"
        params.update(FID_INPUT_DATE_1=(now - timedelta(days=140 if timeframe == Timeframe.D1 else 700)).strftime("%Y%m%d"),
                      FID_INPUT_DATE_2=now.strftime("%Y%m%d"),
                      FID_PERIOD_DIV_CODE="D" if timeframe == Timeframe.D1 else "W",
                      FID_ORG_ADJ_PRC="0")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(f"{BASE}/uapi/domestic-stock/v1/quotations/{path}",
                                    headers={"authorization": f"Bearer {token}", "appkey": key,
                                             "appsecret": secret, "tr_id": tr_id}, params=params)
        response.raise_for_status()
        try:
            payload = response.json()
            if payload["rt_cd"] != "0":
                raise ProviderError
            rows = {}
            for row in payload["output2"]:
                if not row.get("stck_bsop_date"):
                    continue
                date = row["stck_bsop_date"]
                if intraday and date != now.strftime("%Y%m%d"):
                    continue
                value = date + row["stck_cntg_hour"] if intraday else date
                fmt = "%Y%m%d%H%M%S" if intraday else "%Y%m%d"
                timestamp = int(datetime.strptime(value, fmt).replace(tzinfo=zone).timestamp())
                rows[timestamp] = {"time": timestamp, "open": int(row["stck_oprc"]),
                                   "high": int(row["stck_hgpr"]), "low": int(row["stck_lwpr"]),
                                   "close": int(row["stck_prpr" if intraday else "stck_clpr"])}
            return [rows[t] for t in sorted(rows)]
        except (ValueError, KeyError, TypeError) as exc:
            raise ProviderError from exc
