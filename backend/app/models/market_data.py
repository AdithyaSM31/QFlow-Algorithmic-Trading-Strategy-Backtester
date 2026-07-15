"""Market Data model — maps to TimescaleDB hypertable."""

from datetime import datetime

from sqlalchemy import String, Float, BigInteger, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketData(Base):
    """
    OHLCV market data stored in a TimescaleDB hypertable.
    The hypertable is created in init_db.sql with auto-partitioning by timestamp.
    """

    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uq_market_symbol_time"),
    )

    # TimescaleDB hypertables don't require a traditional PK —
    # we use (symbol, timestamp) as the composite unique key.
    # SQLAlchemy needs a PK, so we use timestamp + symbol together.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String, primary_key=True, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adj_close: Mapped[float] = mapped_column(Float, nullable=True)
