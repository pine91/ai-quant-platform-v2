"""Market identifiers shared by future data providers."""
from enum import Enum
from pydantic import BaseModel, Field

class Market(str, Enum):
    CRYPTO = "crypto"
    KR_STOCK = "kr_stock"
    US_STOCK = "us_stock"

class Instrument(BaseModel):
    market: Market
    symbol: str = Field(min_length=1, max_length=32)

    @property
    def currency(self) -> str:
        return "USD" if self.market == Market.US_STOCK else "KRW"
