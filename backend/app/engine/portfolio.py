"""
QFlow Portfolio Tracker — Manages positions, cash, and PnL.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from app.engine.event import (
    SignalEvent, SignalType,
    OrderEvent, OrderType, Direction,
    FillEvent,
)


@dataclass
class Position:
    symbol: str
    quantity: int = 0
    avg_cost: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0


class Portfolio:
    def __init__(self, initial_capital: float = 100_000.0, max_position_pct: float = 0.2):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.max_position_pct = max_position_pct
        self._positions: dict[str, Position] = {}
        self._equity_curve: list[dict] = []
        self._trades_log: list[dict] = []
        self._prev_portfolio_value: float = initial_capital

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions

    @property
    def equity_curve(self) -> list[dict]:
        return self._equity_curve

    @property
    def trades_log(self) -> list[dict]:
        return self._trades_log

    def get_portfolio_value(self) -> float:
        return self.cash + sum(p.market_value for p in self._positions.values())

    def get_positions_dict(self) -> dict[str, int]:
        return {s: p.quantity for s, p in self._positions.items() if p.quantity != 0}

    def get_positions_value(self) -> float:
        return sum(p.market_value for p in self._positions.values())

    def update_market_value(self, symbol: str, current_price: float):
        if symbol in self._positions:
            pos = self._positions[symbol]
            pos.market_value = pos.quantity * current_price
            pos.unrealized_pnl = (current_price - pos.avg_cost) * pos.quantity

    def on_signal(self, signal: SignalEvent) -> OrderEvent | None:
        if signal.signal_type == SignalType.LONG:
            if signal.symbol in self._positions and self._positions[signal.symbol].quantity > 0:
                return None
            allocation = self.initial_capital * self.max_position_pct * signal.strength
            allocation = min(allocation, self.cash * 0.95)
            if allocation < 100:
                return None
            return OrderEvent(
                timestamp=signal.timestamp, symbol=signal.symbol,
                order_type=OrderType.MARKET, direction=Direction.BUY, quantity=0,
            )
        elif signal.signal_type == SignalType.EXIT:
            pos = self._positions.get(signal.symbol)
            if pos is None or pos.quantity <= 0:
                return None
            return OrderEvent(
                timestamp=signal.timestamp, symbol=signal.symbol,
                order_type=OrderType.MARKET, direction=Direction.SELL, quantity=pos.quantity,
            )
        return None

    def calculate_buy_quantity(self, signal: SignalEvent, fill_price: float) -> int:
        allocation = self.initial_capital * self.max_position_pct * signal.strength
        allocation = min(allocation, self.cash * 0.95)
        return max(0, int(allocation / fill_price))

    def on_fill(self, fill: FillEvent):
        symbol = fill.symbol
        if fill.direction == Direction.BUY:
            if symbol not in self._positions:
                self._positions[symbol] = Position(symbol=symbol)
            pos = self._positions[symbol]
            old_value = pos.avg_cost * pos.quantity
            new_value = fill.fill_price * fill.quantity
            new_qty = pos.quantity + fill.quantity
            pos.avg_cost = (old_value + new_value) / new_qty if new_qty > 0 else 0
            pos.quantity = new_qty
            pos.market_value = pos.quantity * fill.fill_price
            self.cash -= (fill.fill_price * fill.quantity + fill.commission)
            pnl = None
        elif fill.direction == Direction.SELL:
            pos = self._positions.get(symbol)
            if pos is None:
                return
            pnl = (fill.fill_price - pos.avg_cost) * fill.quantity - fill.commission
            pos.realized_pnl += pnl
            pos.quantity -= fill.quantity
            pos.market_value = pos.quantity * fill.fill_price
            self.cash += (fill.fill_price * fill.quantity) - fill.commission
        else:
            pnl = None

        self._trades_log.append({
            "timestamp": fill.timestamp, "symbol": fill.symbol,
            "side": fill.direction.value, "quantity": fill.quantity,
            "price": fill.price, "fill_price": fill.fill_price,
            "slippage": fill.slippage, "commission": fill.commission, "pnl": pnl,
        })

    def record_snapshot(self, timestamp: datetime):
        pv = self.get_portfolio_value()
        pval = self.get_positions_value()
        dr = (pv / self._prev_portfolio_value) - 1.0 if self._prev_portfolio_value > 0 else 0.0
        cr = (pv / self.initial_capital) - 1.0
        self._equity_curve.append({
            "timestamp": timestamp, "portfolio_value": pv, "cash": self.cash,
            "positions_value": pval, "positions": self.get_positions_dict(),
            "daily_return": dr, "cumulative_return": cr,
        })
        self._prev_portfolio_value = pv
