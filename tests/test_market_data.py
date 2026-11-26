from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def upstream(monkeypatch):
    original = httpx.AsyncClient

    def register(handler):
        monkeypatch.setattr(
            httpx, "AsyncClient",
            lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
        )

    return register


def stamp(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def yahoo(times):
    n = len(times)
    return {"chart": {"error": None, "result": [{
        "timestamp": [stamp(t) for t in times],
        "indicators": {"quote": [{
            "open": list(range(10, 10+n)), "high": list(range(20, 20+n)),
            "low": list(range(n, 0, -1)), "close": list(range(15, 15+n)),
        }]},
    }]}}


def test_four_hour_regular_ohlc_across_dst(upstream):
    def handle(request):
        assert request.url.params["interval"] == "60m"
        assert request.url.params["includePrePost"] == "false"
        return httpx.Response(200, json=yahoo([
            "2025-03-07T14:30", "2025-03-07T17:30", "2025-03-07T18:30",
            "2025-03-10T13:30", "2025-03-10T16:30", "2025-03-10T17:30",
        ]))

    upstream(handle)
    response = TestClient(app).get("/api/markets/us_stock/candles?symbol=AAPL&timeframe=4h")
    assert response.status_code == 200
    rows = response.json()["candles"]
    assert [row["time"] for row in rows] == [stamp(t) for t in (
        "2025-03-07T14:30", "2025-03-07T18:30", "2025-03-10T13:30", "2025-03-10T17:30",
    )]
    assert rows[0] == {"time": stamp("2025-03-07T14:30"), "open": 10, "high": 21, "low": 5, "close": 16}


def test_pre_market_excludes_regular_and_weekends(upstream):
    upstream(lambda request: httpx.Response(200, json=yahoo([
        "2025-03-07T09:00", "2025-03-07T14:30",
        "2025-03-08T09:00", "2025-03-10T08:00", "2025-03-10T13:30",
    ])))
    response = TestClient(app).get("/api/markets/us_stock/candles?symbol=AAPL&session=pre")
    assert response.status_code == 200
    assert [row["time"] for row in response.json()["candles"]] == [
        stamp("2025-03-07T09:00"), stamp("2025-03-10T08:00"),
    ]


@pytest.mark.parametrize(("code", "payload", "expected"), [
    (200, {"chart": {"result": [{"meta": {}}], "error": None}}, 200),
    (200, {"chart": {"result": None, "error": {"code": "Not Found"}}}, 502),
    (429, {}, 502),
])
def test_provider_empty_or_unavailable(upstream, code, payload, expected):
    upstream(lambda request: httpx.Response(code, json=payload))
    response = TestClient(app).get("/api/markets/us_stock/candles?symbol=AAPL")
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["candles"] == []


@pytest.mark.parametrize(("venue", "market_code"), [("krx", "J"), ("nxt", "NX")])
def test_kis_venue_is_sent_to_provider(upstream, monkeypatch, venue, market_code):
    for name in ("KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCESS_TOKEN"):
        monkeypatch.setenv(name, "fixture")

    def handle(request):
        assert request.url.host == "openapi.koreainvestment.com"
        assert request.url.params["FID_COND_MRKT_DIV_CODE"] == market_code
        assert request.url.params["FID_INPUT_ISCD"] == "247540"
        assert request.headers["tr_id"] == "FHKST03010100"
        return httpx.Response(200, json={"rt_cd": "0", "output2": [{
            "stck_bsop_date": "20250310", "stck_oprc": "100", "stck_hgpr": "110",
            "stck_lwpr": "99", "stck_clpr": "105",
        }]})

    upstream(handle)
    response = TestClient(app).get(f"/api/markets/kr_stock/candles?symbol=247540.KQ&venue={venue}&timeframe=1d")
    assert response.status_code == 200
    assert response.json()["venue"] == venue
    assert response.json()["candles"][0]["close"] == 105


def test_nxt_without_credentials_returns_unconfigured(upstream, monkeypatch):
    monkeypatch.delenv("KIS_ACCESS_TOKEN", raising=False)

    def unexpected(request):
        pytest.fail("NXT must not fall back to another provider")

    upstream(unexpected)
    response = TestClient(app).get("/api/markets/kr_stock/candles?symbol=005930&venue=nxt&timeframe=1m")
    assert response.status_code == 503
    assert response.json()["detail"] == "KIS quotes not configured"
