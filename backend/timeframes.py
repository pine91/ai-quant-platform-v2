from enum import Enum

class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

DEFAULT_TIMEFRAME = Timeframe.M5

# Provider mappings; 4h stock candles require session-aware aggregation.
BITHUMB_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
YAHOO_INTERVALS = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "1d": "1d", "1w": "1wk"}
YAHOO_RANGES = {"1m": "5d", "5m": "1mo", "15m": "1mo", "30m": "1mo", "1h": "6mo", "1d": "6mo", "1w": "2y"}
