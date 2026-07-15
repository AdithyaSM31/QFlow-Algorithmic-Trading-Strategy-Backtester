"""
QFlow Analytics Calculator — computes institutional-grade risk metrics.

Calculates Sharpe, Sortino, Max Drawdown, Calmar, Win Rate,
Profit Factor, Alpha, Beta, and more from the equity curve and trades.
"""

from __future__ import annotations
import numpy as np
from typing import Any

RISK_FREE_RATE = 0.04  # 4% annualized
TRADING_DAYS = 252


def compute_analytics(
    equity_curve: list[dict],
    trades: list[dict],
    initial_capital: float = 100_000.0,
) -> dict[str, Any]:
    """Compute full analytics from equity curve and trade log."""
    if not equity_curve or len(equity_curve) < 2:
        return _empty_analytics()

    daily_returns = np.array([p["daily_return"] for p in equity_curve])
    portfolio_values = np.array([p["portfolio_value"] for p in equity_curve])

    # Filter out zero-length returns at the start
    nonzero_start = 0
    for i, r in enumerate(daily_returns):
        if r != 0.0:
            nonzero_start = max(0, i - 1)
            break

    dr = daily_returns[nonzero_start:]
    pv = portfolio_values[nonzero_start:]
    n_days = len(dr)

    if n_days < 2:
        return _empty_analytics()

    # Total and annualized return
    total_return = (pv[-1] / initial_capital) - 1.0
    years = n_days / TRADING_DAYS
    annualized_return = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    # Volatility
    volatility = float(np.std(dr, ddof=1) * np.sqrt(TRADING_DAYS))

    # Sharpe Ratio
    excess_daily = dr - (RISK_FREE_RATE / TRADING_DAYS)
    sharpe = float(np.mean(excess_daily) / np.std(excess_daily, ddof=1) * np.sqrt(TRADING_DAYS)) if np.std(excess_daily, ddof=1) > 0 else 0.0

    # Sortino Ratio (downside deviation only)
    downside = dr[dr < 0]
    downside_std = float(np.std(downside, ddof=1)) if len(downside) > 1 else 1e-10
    sortino = float((np.mean(dr) - RISK_FREE_RATE / TRADING_DAYS) / downside_std * np.sqrt(TRADING_DAYS))

    # Max Drawdown
    peak = np.maximum.accumulate(pv)
    drawdowns = (pv - peak) / peak
    max_drawdown = float(np.min(drawdowns))

    # Max Drawdown Duration (days)
    dd_duration = _max_drawdown_duration(pv)

    # Calmar Ratio
    calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0.0

    # Trade statistics
    trade_pnls = [t["pnl"] for t in trades if t.get("pnl") is not None]
    total_trades = len(trade_pnls)
    wins = [p for p in trade_pnls if p > 0]
    losses = [p for p in trade_pnls if p <= 0]

    win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
    avg_trade_pnl = float(np.mean(trade_pnls)) if trade_pnls else 0.0
    best_trade = float(max(trade_pnls)) if trade_pnls else 0.0
    worst_trade = float(min(trade_pnls)) if trade_pnls else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 1e-10
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss) if total_trades > 0 else 0.0

    return {
        "total_return": float(round(total_return, 6)),
        "annualized_return": float(round(annualized_return, 6)),
        "sharpe_ratio": float(round(sharpe, 4)),
        "sortino_ratio": float(round(sortino, 4)),
        "max_drawdown": float(round(max_drawdown, 6)),
        "max_drawdown_duration_days": int(dd_duration),
        "calmar_ratio": float(round(calmar, 4)),
        "win_rate": float(round(win_rate, 4)),
        "profit_factor": float(round(profit_factor, 4)),
        "total_trades": int(total_trades),
        "avg_trade_pnl": float(round(avg_trade_pnl, 2)),
        "best_trade": float(round(best_trade, 2)),
        "worst_trade": float(round(worst_trade, 2)),
        "volatility": float(round(volatility, 6)),
        "beta": None,  # Computed separately with benchmark data
        "alpha": None,
        "avg_win": float(round(avg_win, 2)),
        "avg_loss": float(round(avg_loss, 2)),
        "expectancy": float(round(expectancy, 2)),
    }


def _max_drawdown_duration(portfolio_values: np.ndarray) -> int:
    peak = portfolio_values[0]
    max_duration = 0
    current_duration = 0
    for val in portfolio_values:
        if val >= peak:
            peak = val
            current_duration = 0
        else:
            current_duration += 1
            max_duration = max(max_duration, current_duration)
    return max_duration


def _empty_analytics() -> dict[str, Any]:
    return {
        "total_return": 0.0, "annualized_return": 0.0,
        "sharpe_ratio": 0.0, "sortino_ratio": 0.0,
        "max_drawdown": 0.0, "max_drawdown_duration_days": 0,
        "calmar_ratio": 0.0, "win_rate": 0.0, "profit_factor": 0.0,
        "total_trades": 0, "avg_trade_pnl": 0.0,
        "best_trade": 0.0, "worst_trade": 0.0,
        "volatility": 0.0, "beta": None, "alpha": None,
        "avg_win": 0.0, "avg_loss": 0.0, "expectancy": 0.0,
    }
