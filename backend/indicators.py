"""Indicators calculated from ascending candle timestamps."""


def ema(rows, period):
    if len(rows) < period:
        return []
    value = sum(row["close"] for row in rows[:period]) / period
    result = [{"time": rows[period - 1]["time"], "value": value}]
    weight = 2 / (period + 1)
    for row in rows[period:]:
        value += weight * (row["close"] - value)
        result.append({"time": row["time"], "value": value})
    return result


def rsi(rows, period=14):
    if len(rows) <= period:
        return []
    changes = [current["close"] - previous["close"] for previous, current in zip(rows, rows[1:])]
    gain = sum(max(change, 0) for change in changes[:period]) / period
    loss = sum(max(-change, 0) for change in changes[:period]) / period
    result = []
    for index in range(period, len(rows)):
        if index > period:
            change = changes[index - 1]
            gain = (gain * (period - 1) + max(change, 0)) / period
            loss = (loss * (period - 1) + max(-change, 0)) / period
        value = 100 * gain / (gain + loss) if gain + loss else 50
        result.append({"time": rows[index]["time"], "value": value})
    return result


def indicators(rows):
    levels = []
    if rows:
        low = min(row["low"] for row in rows)
        high = max(row["high"] for row in rows)
        if high > low:
            levels = [{"ratio": ratio, "value": high - (high - low) * ratio}
                      for ratio in (0.236, 0.382, 0.5, 0.618, 0.786)]
    return {"ema20": ema(rows, 20), "ema60": ema(rows, 60), "rsi14": rsi(rows),
            "fibonacci": levels}
