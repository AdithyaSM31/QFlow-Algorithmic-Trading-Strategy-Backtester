"""
QFlow Execution Simulator — models real-world market friction.

Applies slippage (basis points) and commission (percentage) to orders.
Fills at next bar's open price, NOT current bar's close —
preventing the common bias of trading at signal-generation price.
"""

from __future__ import annotations
from app.engine.event import OrderEvent, FillEvent, Direction


class ExecutionSimulator:
    def __init__(self, slippage_bps: float = 5.0, commission_pct: float = 0.1):
        self.slippage_bps = slippage_bps
        self.commission_pct = commission_pct

    def execute(self, order: OrderEvent, fill_price: float) -> FillEvent:
        """
        Execute an order at the given fill_price (next bar's open).
        Apply slippage and commission to model real trading costs.
        """
        # Slippage: BUY gets a worse (higher) price, SELL gets worse (lower)
        slippage_fraction = self.slippage_bps / 10_000.0
        if order.direction == Direction.BUY:
            actual_price = fill_price * (1.0 + slippage_fraction)
        else:
            actual_price = fill_price * (1.0 - slippage_fraction)

        slippage_amount = abs(actual_price - fill_price) * order.quantity
        commission = actual_price * order.quantity * (self.commission_pct / 100.0)

        return FillEvent(
            timestamp=order.timestamp,
            symbol=order.symbol,
            direction=order.direction,
            quantity=order.quantity,
            price=fill_price,
            fill_price=actual_price,
            commission=commission,
            slippage=slippage_amount,
        )
