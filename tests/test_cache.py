import asyncio

from redis.exceptions import ConnectionError

from backend.cache import cached_candles


def test_cache_hit_and_outage(monkeypatch):
    from backend import cache
    backend = {}

    class FakeRedis:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def get(self, key):
            if backend.get("offline"):
                raise ConnectionError
            return backend.get(key)

        async def set(self, key, value, ex):
            assert ex == 30
            if backend.get("offline"):
                raise ConnectionError
            backend[key] = value

    monkeypatch.setenv("REDIS_URL", "redis://fixture")
    monkeypatch.setattr(cache.Redis, "from_url", lambda *args, **kwargs: FakeRedis())
    calls = []

    async def load():
        calls.append(1)
        return [{"time": 1}]

    async def scenario():
        assert await cached_candles("test", load) == [{"time": 1}]
        assert await cached_candles("test", load) == [{"time": 1}]
        assert len(calls) == 1
        backend["offline"] = True
        assert await cached_candles("test", load) == [{"time": 1}]
        assert len(calls) == 2

    asyncio.run(scenario())
