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
