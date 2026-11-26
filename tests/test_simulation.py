import pytest

from backend.simulation import backtest


def test_signals_use_next_open_and_charge_costs():
    closes = [100.0] * 60 + [110.0, 120.0] + [50.0] * 3
    bars = [{"time": i, "open": close + 1, "close": close} for i, close in enumerate(closes)]
    initial = 10_000
    short = backtest(bars[:61], initial, 10, 5)
    full = backtest(bars, initial, 10, 5)
    assert short["trades"] == []
    assert full["equity"][:61] == short["equity"]
    buy, sell = full["trades"]
    assert buy["time"] == 61
    assert buy["price"] == pytest.approx(121 * 1.0005)
    assert buy["fee"] == pytest.approx(buy["quantity"] * buy["price"] * 0.001)
    assert sell["price"] == pytest.approx(51 * 0.9995)
    assert full["final_equity"] == pytest.approx(sell["quantity"] * sell["price"] - sell["fee"])
