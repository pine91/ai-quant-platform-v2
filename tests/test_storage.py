from uuid import uuid4

from alembic import command
from alembic.config import Config
import httpx
from fastapi.testclient import TestClient

from backend.main import app


def test_migrated_paper_account_executes_and_retries_without_quotes(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'paper.sqlite3').as_posix()}")
    command.upgrade(Config("alembic.ini"), "head")
    original = httpx.AsyncClient
    requests = []

    def provider(request):
        requests.append(request)
        return httpx.Response(200, json=[{
            "candle_date_time_utc": "2025-03-10T13:30:00", "opening_price": 100,
            "high_price": 100, "low_price": 100, "trade_price": 100,
        }])

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(provider), **kw))
    client = TestClient(app)
    path = "/api/markets/crypto/paper?symbol=BTC-KRW"
    order = {"request_id": str(uuid4()), "side": "buy", "quantity": "2"}
    first = client.post(path, json=order)
    assert first.status_code == 200, first.text
    assert float(first.json()["price"]) == 100.05
    assert float(first.json()["fee"]) == 0.2001
    assert client.post(path, json=order).json() == first.json()
    assert len(requests) == 1
    assert client.post(path, json={**order, "quantity": "3"}).status_code == 422
    assert client.post(path, json={
        "request_id": str(uuid4()), "side": "sell", "quantity": "3",
    }).status_code == 422
    account = client.get(path).json()
    assert float(account["units"]) == 2
    assert len(account["fills"]) == 1
