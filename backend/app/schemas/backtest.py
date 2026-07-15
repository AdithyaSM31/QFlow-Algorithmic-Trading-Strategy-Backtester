"""Backtest schemas — submit, status, results, analytics."""

from datetime import datetime, date
from pydantic import BaseModel, Field
from uuid import UUID


class BacktestCreate(BaseModel):
    strategy_id: UUID
    symbols: list[str] = Field(..., min_length=1, max_length=10)
    start_date: date
    end_date: date
    initial_capital: float = Field(default=100_000.0, ge=1_000, le=100_000_000)
    slippage_bps: float = Field(default=5.0, ge=0, le=100)
    commission_pct: float = Field(default=0.1, ge=0, le=5)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "strategy_id": "uuid-here",
                    "symbols": ["AAPL", "GOOGL"],
                    "start_date": "2020-01-01",
                    "end_date": "2024-12-31",
                    "initial_capital": 100000,
                    "slippage_bps": 5,
                    "commission_pct": 0.1,
                }
            ]
        }
    }


class BacktestResponse(BaseModel):
    id: UUID
    strategy_id: UUID
    user_id: UUID
    status: str
    symbols: list[str]
    start_date: date
    end_date: date
    initial_capital: float
    slippage_bps: float
    commission_pct: float
    progress: float
    celery_task_id: str | None
    submitted_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class BacktestResultPoint(BaseModel):
    timestamp: datetime
    portfolio_value: float
    cash: float
    positions_value: float
    positions: dict
    daily_return: float
    cumulative_return: float

    model_config = {"from_attributes": True}


class TradeResponse(BaseModel):
    id: UUID
    timestamp: datetime
    symbol: str
    side: str
    quantity: int
    price: float
    fill_price: float
    slippage: float
    commission: float
    pnl: float | None

    model_config = {"from_attributes": True}


class AnalyticsResponse(BaseModel):
    backtest_id: UUID
    total_return: float | None
    annualized_return: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    max_drawdown: float | None
    max_drawdown_duration_days: int | None
    calmar_ratio: float | None
    win_rate: float | None
    profit_factor: float | None
    total_trades: int | None
    avg_trade_pnl: float | None
    best_trade: float | None
    worst_trade: float | None
    volatility: float | None
    beta: float | None
    alpha: float | None
    avg_win: float | None
    avg_loss: float | None
    expectancy: float | None

    model_config = {"from_attributes": True}


class BacktestFullResponse(BaseModel):
    """Complete backtest response with embedded analytics."""

    backtest: BacktestResponse
    analytics: AnalyticsResponse | None = None
    strategy_name: str | None = None
    strategy_type: str | None = None
