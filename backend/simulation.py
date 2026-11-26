"""Long-only EMA crossover simulation with next-open execution."""
from .indicators import ema


def execution_price(price, side, slippage_bps):
    return price * (1 + side * slippage_bps / 10_000)


def backtest(rows, initial_cash, fee_bps, slippage_bps):
    fast = {point["time"]: point["value"] for point in ema(rows, 20)}
    slow = {point["time"]: point["value"] for point in ema(rows, 60)}
    cash, units, equity, trades = initial_cash, 0.0, [], []
    previous, pending = None, 0
    for bar in rows:
        if pending:
            price = execution_price(bar["open"], pending, slippage_bps)
            if pending == 1:
                units = cash / (price * (1 + fee_bps / 10_000))
                quantity = units
                fee = units * price * fee_bps / 10_000
                cash = 0.0
            else:
                quantity = units
                fee = units * price * fee_bps / 10_000
                cash = units * price - fee
                units = 0.0
            trades.append({"time": bar["time"], "side": "buy" if pending == 1 else "sell",
                           "price": price, "quantity": quantity, "fee": fee})
            pending = 0
        equity.append({"time": bar["time"], "value": cash + units * bar["close"]})
        if bar["time"] in slow:
            above = fast[bar["time"]] > slow[bar["time"]]
            if previous is not None and above != previous:
                if above and cash:
                    pending = 1
                elif not above and units:
                    pending = -1
            previous = above
    final_equity = equity[-1]["value"] if equity else initial_cash
    return {"initial_cash": initial_cash, "final_equity": final_equity,
            "return_pct": 100 * (final_equity / initial_cash - 1), "trades": trades, "equity": equity}
