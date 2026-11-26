import pytest

from backend.indicators import indicators


def test_indicator_warmup_and_linear_sequence():
    rows = [{"time": i, "close": i + 10, "low": i + 9, "high": i + 11} for i in range(61)]
    result = indicators(rows)
    assert result["ema20"][0] == {"time": 19, "value": 19.5}
    assert result["ema20"][-1] == {"time": 60, "value": 60.5}
    assert result["ema60"][0] == {"time": 59, "value": 39.5}
    assert result["rsi14"][0] == {"time": 14, "value": 100}
    assert result["fibonacci"][0]["value"] == pytest.approx(71 - 62 * 0.236)


def test_empty_and_flat_prices():
    assert all(not values for values in indicators([]).values())
    result = indicators([{"time": i, "close": 10, "low": 10, "high": 10} for i in range(15)])
    assert result["rsi14"] == [{"time": 14, "value": 50}]
    assert result["fibonacci"] == []
