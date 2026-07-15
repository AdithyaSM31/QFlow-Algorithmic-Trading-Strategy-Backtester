"""
QFlow Engine Runner — Main event loop orchestrating the backtest.

This is the heart of the system. It drives the simulation by:
1. Pulling bars from DataHandler one at a time
2. Passing MarketEvents to the Strategy
3. Converting SignalEvents to OrderEvents via Portfolio
4. Executing orders through ExecutionSimulator
5. Recording portfolio snapshots for the equity curve

The event loop ensures strict temporal ordering — no look-ahead.
"""

from __future__ import annotations
import logging
from typing import Callable

import pandas as pd

from app.engine.data_handler import DataHandler
from app.engine.strategy import BaseStrategy, create_strategy
from app.engine.portfolio import Portfolio
from app.engine.execution import ExecutionSimulator
from app.engine.analytics import compute_analytics
from app.engine.event import Direction

logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    Orchestrates an event-driven backtest simulation.
    """

    def __init__(
        self,
        data: dict[str, pd.DataFrame],
        strategy_type: str,
        strategy_params: dict,
        initial_capital: float = 100_000.0,
        slippage_bps: float = 5.0,
        commission_pct: float = 0.1,
        progress_callback: Callable[[float], None] | None = None,
    ):
        self.data_handler = DataHandler(data)
        self.strategy = create_strategy(strategy_type, strategy_params)
        self.portfolio = Portfolio(initial_capital=initial_capital)
        self.executor = ExecutionSimulator(
            slippage_bps=slippage_bps,
            commission_pct=commission_pct,
        )
        self._progress_callback = progress_callback
        self._pending_orders: list = []
        self._pending_signals: list = []

    def run(self) -> dict:
        """
        Execute the full backtest and return results.
        
        Returns dict with keys: equity_curve, trades, analytics
        """
        logger.info(
            f"Starting backtest: {self.strategy.__class__.__name__} "
            f"on {self.data_handler.symbols} "
            f"({self.data_handler.total_bars} bars)"
        )

        bar_count = 0
        last_progress = 0.0

        while True:
            # 1. Get next bar (advances pointer by 1)
            market_events = self.data_handler.get_next_bar()
            if market_events is None:
                break

            # 2. Execute any pending orders from previous bar
            #    (fills at CURRENT bar's open, not previous bar's close)
            self._execute_pending_orders(market_events)

            # 3. Update portfolio market values with current prices
            for event in market_events:
                self.portfolio.update_market_value(event.symbol, event.close)

            # 4. Pass market events to strategy
            for event in market_events:
                signals = self.strategy.on_market(event, self.data_handler)
                for signal in signals:
                    # 5. Convert signals to orders
                    order = self.portfolio.on_signal(signal)
                    if order is not None:
                        # Store order + signal for next bar execution
                        self._pending_orders.append((order, signal))

            # 6. Record portfolio snapshot
            timestamp = self.data_handler.get_current_timestamp()
            if timestamp:
                self.portfolio.record_snapshot(timestamp)

            # 7. Report progress
            bar_count += 1
            progress = self.data_handler.progress
            if self._progress_callback and progress - last_progress >= 0.05:
                self._progress_callback(progress)
                last_progress = progress

        # Final progress
        if self._progress_callback:
            self._progress_callback(1.0)

        # Compute analytics
        analytics = compute_analytics(
            self.portfolio.equity_curve,
            self.portfolio.trades_log,
            self.portfolio.initial_capital,
        )

        logger.info(
            f"Backtest complete: {bar_count} bars processed, "
            f"{analytics['total_trades']} trades, "
            f"return={analytics['total_return']:.2%}"
        )

        return {
            "equity_curve": self.portfolio.equity_curve,
            "trades": self.portfolio.trades_log,
            "analytics": analytics,
        }

    def _execute_pending_orders(self, market_events: list):
        """
        Execute orders from the PREVIOUS bar using CURRENT bar's open.
        
        This is critical for realism: you can't trade at the price
        that generated your signal. Orders fill at the next bar's open.
        """
        if not self._pending_orders:
            return

        # Build price lookup for current bar
        prices = {e.symbol: e.open for e in market_events}

        for order, signal in self._pending_orders:
            if order.symbol not in prices:
                continue

            fill_price = prices[order.symbol]

            # For buy orders, calculate quantity now that we know the price
            if order.direction == Direction.BUY:
                quantity = self.portfolio.calculate_buy_quantity(signal, fill_price)
                if quantity <= 0:
                    continue
                # Create a new order with the computed quantity
                from app.engine.event import OrderEvent
                order = OrderEvent(
                    timestamp=order.timestamp,
                    symbol=order.symbol,
                    order_type=order.order_type,
                    direction=order.direction,
                    quantity=quantity,
                )

            fill = self.executor.execute(order, fill_price)
            self.portfolio.on_fill(fill)

        self._pending_orders.clear()
