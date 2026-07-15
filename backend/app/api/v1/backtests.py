"""Backtest routes — submit, list, status, results, analytics."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.backtest import Backtest, BacktestResult, Trade, BacktestAnalytics
from app.models.strategy import Strategy
from app.schemas.backtest import (
    BacktestCreate, BacktestResponse, BacktestResultPoint,
    TradeResponse, AnalyticsResponse, BacktestFullResponse,
)
from app.api.deps import get_current_user
from app.workers.tasks import run_backtest

router = APIRouter()


def _route_to_queue(start_date, end_date) -> str:
    """Route backtest to fast or slow queue based on date range."""
    delta = end_date - start_date
    return "fast" if delta < timedelta(days=365) else "slow"


@router.post("/", response_model=BacktestResponse, status_code=202)
async def submit_backtest(
    payload: BacktestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a new backtest job → returns immediately with job ID."""
    # Validate strategy exists and belongs to user
    result = await db.execute(
        select(Strategy).where(Strategy.id == payload.strategy_id, Strategy.user_id == user.id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if payload.start_date >= payload.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    backtest = Backtest(
        strategy_id=strategy.id,
        user_id=user.id,
        symbols=payload.symbols,
        start_date=payload.start_date,
        end_date=payload.end_date,
        initial_capital=payload.initial_capital,
        slippage_bps=payload.slippage_bps,
        commission_pct=payload.commission_pct,
    )
    db.add(backtest)
    await db.flush()
    await db.refresh(backtest)

    # Route to appropriate queue and dispatch
    queue = _route_to_queue(payload.start_date, payload.end_date)
    task = run_backtest.apply_async(
        args=[str(backtest.id)],
        queue=queue,
    )
    backtest.celery_task_id = task.id
    await db.commit()

    return backtest


@router.get("/", response_model=list[BacktestResponse])
async def list_backtests(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = None,
    limit: int = 50,
):
    query = select(Backtest).where(Backtest.user_id == user.id)
    if status:
        query = query.where(Backtest.status == status)
    query = query.order_by(Backtest.submitted_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{backtest_id}", response_model=BacktestFullResponse)
async def get_backtest(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id, Backtest.user_id == user.id)
    )
    backtest = result.scalar_one_or_none()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # Load analytics if available
    analytics_result = await db.execute(
        select(BacktestAnalytics).where(BacktestAnalytics.backtest_id == backtest_id)
    )
    analytics = analytics_result.scalar_one_or_none()

    # Load strategy info
    strategy_result = await db.execute(
        select(Strategy).where(Strategy.id == backtest.strategy_id)
    )
    strategy = strategy_result.scalar_one_or_none()

    return BacktestFullResponse(
        backtest=backtest,
        analytics=analytics,
        strategy_name=strategy.name if strategy else None,
        strategy_type=strategy.type if strategy else None,
    )


@router.get("/{backtest_id}/equity", response_model=list[BacktestResultPoint])
async def get_equity_curve(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership
    bt = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id, Backtest.user_id == user.id)
    )
    if not bt.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backtest not found")

    result = await db.execute(
        select(BacktestResult)
        .where(BacktestResult.backtest_id == backtest_id)
        .order_by(BacktestResult.timestamp.asc())
    )
    return result.scalars().all()


@router.get("/{backtest_id}/trades", response_model=list[TradeResponse])
async def get_trades(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bt = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id, Backtest.user_id == user.id)
    )
    if not bt.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backtest not found")

    result = await db.execute(
        select(Trade)
        .where(Trade.backtest_id == backtest_id)
        .order_by(Trade.timestamp.asc())
    )
    return result.scalars().all()


@router.get("/{backtest_id}/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    backtest_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bt = await db.execute(
        select(Backtest).where(Backtest.id == backtest_id, Backtest.user_id == user.id)
    )
    if not bt.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backtest not found")

    result = await db.execute(
        select(BacktestAnalytics).where(BacktestAnalytics.backtest_id == backtest_id)
    )
    analytics = result.scalar_one_or_none()
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not yet available")
    return analytics
