"""
QFlow Celery Tasks — Backtest execution task.

This task runs on a Celery worker process. It:
1. Loads strategy config and market data from the database
2. Runs the event-driven backtest engine
3. Stores results (equity curve, trades, analytics) back to the DB
4. Publishes progress updates via Redis pub/sub
"""

import logging
import json
from datetime import datetime, timezone

import pandas as pd
import redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.config import get_settings
from app.engine.runner import BacktestRunner

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_sync_engine():
    """Create a synchronous SQLAlchemy engine for Celery workers."""
    return create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)


def _get_redis():
    """Create a Redis client for pub/sub progress updates."""
    return redis.from_url(settings.REDIS_URL)


@celery_app.task(bind=True, name="run_backtest", max_retries=1)
def run_backtest(self, backtest_id: str):
    """
    Execute a backtest job.
    
    This is a CPU-intensive task that runs on a dedicated worker.
    Progress updates are published via Redis pub/sub for real-time
    WebSocket streaming to the frontend.
    """
    engine = _get_sync_engine()
    redis_client = _get_redis()

    try:
        with Session(engine) as session:
            # 1. Load backtest config
            row = session.execute(
                text("SELECT * FROM backtests WHERE id = :id"),
                {"id": backtest_id}
            ).mappings().first()

            if row is None:
                raise ValueError(f"Backtest {backtest_id} not found")

            # 2. Update status to RUNNING
            session.execute(
                text("UPDATE backtests SET status = 'RUNNING', started_at = :now WHERE id = :id"),
                {"id": backtest_id, "now": datetime.now(timezone.utc)}
            )
            session.commit()

            # 3. Load strategy
            strategy_row = session.execute(
                text("SELECT * FROM strategies WHERE id = :id"),
                {"id": str(row["strategy_id"])}
            ).mappings().first()

            if strategy_row is None:
                raise ValueError(f"Strategy {row['strategy_id']} not found")

            # 4. Load market data for each symbol
            symbols = row["symbols"]
            start_date = row["start_date"]
            end_date = row["end_date"]

            data = {}
            for symbol in symbols:
                result = session.execute(
                    text("""
                        SELECT timestamp, open, high, low, close, volume
                        FROM market_data
                        WHERE symbol = :symbol
                          AND timestamp >= :start
                          AND timestamp <= :end
                        ORDER BY timestamp ASC
                    """),
                    {"symbol": symbol, "start": start_date, "end": end_date}
                ).mappings().all()

                if not result:
                    raise ValueError(f"No market data for {symbol} in range {start_date} to {end_date}")

                df = pd.DataFrame(result)
                data[symbol] = df

            # 5. Progress callback via Redis pub/sub
            def progress_callback(progress: float):
                session.execute(
                    text("UPDATE backtests SET progress = :p WHERE id = :id"),
                    {"p": progress, "id": backtest_id}
                )
                session.commit()
                redis_client.publish(
                    "backtest_progress",
                    json.dumps({"backtest_id": backtest_id, "progress": progress, "status": "RUNNING"})
                )

            # 6. Run the backtest engine
            runner = BacktestRunner(
                data=data,
                strategy_type=strategy_row["type"],
                strategy_params=strategy_row["parameters"],
                initial_capital=row["initial_capital"],
                slippage_bps=row["slippage_bps"],
                commission_pct=row["commission_pct"],
                progress_callback=progress_callback,
            )
            results = runner.run()

            # 7. Store equity curve
            for point in results["equity_curve"]:
                session.execute(
                    text("""
                        INSERT INTO backtest_results
                        (backtest_id, timestamp, portfolio_value, cash, positions_value,
                         positions, daily_return, cumulative_return)
                        VALUES (:bid, :ts, :pv, :cash, :posv, :pos, :dr, :cr)
                    """),
                    {
                        "bid": backtest_id, "ts": point["timestamp"],
                        "pv": point["portfolio_value"], "cash": point["cash"],
                        "posv": point["positions_value"],
                        "pos": json.dumps(point["positions"]),
                        "dr": point["daily_return"], "cr": point["cumulative_return"],
                    }
                )

            # 8. Store trades
            for trade in results["trades"]:
                session.execute(
                    text("""
                        INSERT INTO trades
                        (backtest_id, timestamp, symbol, side, quantity,
                         price, fill_price, slippage, commission, pnl)
                        VALUES (:bid, :ts, :sym, :side, :qty, :price, :fp, :slip, :comm, :pnl)
                    """),
                    {
                        "bid": backtest_id, "ts": trade["timestamp"],
                        "sym": trade["symbol"], "side": trade["side"],
                        "qty": trade["quantity"], "price": trade["price"],
                        "fp": trade["fill_price"], "slip": trade["slippage"],
                        "comm": trade["commission"], "pnl": trade.get("pnl"),
                    }
                )

            # 9. Store analytics
            analytics = results["analytics"]
            cols = ", ".join(["backtest_id"] + list(analytics.keys()))
            placeholders = ", ".join([":backtest_id"] + [f":{k}" for k in analytics.keys()])
            session.execute(
                text(f"INSERT INTO backtest_analytics ({cols}) VALUES ({placeholders})"),
                {"backtest_id": backtest_id, **analytics}
            )

            # 10. Mark as completed
            session.execute(
                text("""
                    UPDATE backtests
                    SET status = 'COMPLETED', completed_at = :now, progress = 1.0
                    WHERE id = :id
                """),
                {"id": backtest_id, "now": datetime.now(timezone.utc)}
            )
            session.commit()

            # Publish completion
            redis_client.publish(
                "backtest_progress",
                json.dumps({"backtest_id": backtest_id, "progress": 1.0, "status": "COMPLETED"})
            )

            logger.info(f"Backtest {backtest_id} completed successfully")
            return {"status": "COMPLETED", "backtest_id": backtest_id}

    except Exception as exc:
        logger.error(f"Backtest {backtest_id} failed: {exc}")
        try:
            with Session(engine) as session:
                session.execute(
                    text("""
                        UPDATE backtests
                        SET status = 'FAILED', error_message = :err, completed_at = :now
                        WHERE id = :id
                    """),
                    {"id": backtest_id, "err": str(exc), "now": datetime.now(timezone.utc)}
                )
                session.commit()
                redis_client.publish(
                    "backtest_progress",
                    json.dumps({"backtest_id": backtest_id, "progress": 0, "status": "FAILED", "error": str(exc)})
                )
        except Exception:
            pass
        raise
