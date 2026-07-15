"""Market data schemas."""

from datetime import datetime
from pydantic import BaseModel


class OHLCVBar(BaseModel):
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float | None = None

    model_config = {"from_attributes": True}


class SymbolInfo(BaseModel):
    symbol: str
    first_date: datetime
    last_date: datetime
    total_bars: int


class MarketDataQuery(BaseModel):
    symbol: str
    start_date: datetime | None = None
    end_date: datetime | None = None
    timeframe: str = "1d"  # 1d, 1w
