"""
QFlow Event Types — the vocabulary of the event-driven engine.

Events flow through the system in a strict pipeline:
  MarketEvent → Strategy → SignalEvent → Portfolio → OrderEvent → Execution → FillEvent → Portfolio

This separation of concerns is what production trading systems use
and is a key interview talking point.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    MARKET = "MARKET"
    SIGNAL = "SIGNAL"
    ORDER = "ORDER"
    FILL = "FILL"


class SignalType(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    EXIT = "EXIT"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class MarketEvent:
    """
    Emitted by DataHandler for each new bar of data.
    Contains OHLCV data for a single symbol at a single timestamp.
    
    CRITICAL: This is the ONLY way strategies receive market data.
    The frozen=True ensures events are immutable — strategies
    cannot tamper with historical data.
    """

    event_type: EventType = field(default=EventType.MARKET, init=False)
    timestamp: datetime = field(default=None)
    symbol: str = field(default="")
    open: float = field(default=0.0)
    high: float = field(default=0.0)
    low: float = field(default=0.0)
    close: float = field(default=0.0)
    volume: int = field(default=0)


@dataclass(frozen=True)
class SignalEvent:
    """
    Emitted by Strategy when a trading signal is generated.
    Contains signal direction and strength (0.0 to 1.0).
    """

    event_type: EventType = field(default=EventType.SIGNAL, init=False)
    timestamp: datetime = field(default=None)
    symbol: str = field(default="")
    signal_type: SignalType = field(default=SignalType.LONG)
    strength: float = field(default=1.0)  # 0.0 to 1.0


@dataclass(frozen=True)
class OrderEvent:
    """
    Emitted by Portfolio to request trade execution.
    Translates signals into concrete orders with quantities.
    """

    event_type: EventType = field(default=EventType.ORDER, init=False)
    timestamp: datetime = field(default=None)
    symbol: str = field(default="")
    order_type: OrderType = field(default=OrderType.MARKET)
    direction: Direction = field(default=Direction.BUY)
    quantity: int = field(default=0)


@dataclass(frozen=True)
class FillEvent:
    """
    Emitted by ExecutionSimulator after processing an order.
    Contains the actual fill price (including slippage) and commission.
    
    NOTE: fill_price != price. The difference is slippage —
    this models real market friction.
    """

    event_type: EventType = field(default=EventType.FILL, init=False)
    timestamp: datetime = field(default=None)
    symbol: str = field(default="")
    direction: Direction = field(default=Direction.BUY)
    quantity: int = field(default=0)
    price: float = field(default=0.0)        # Raw market price
    fill_price: float = field(default=0.0)   # After slippage
    commission: float = field(default=0.0)    # Transaction cost
    slippage: float = field(default=0.0)      # Slippage amount
