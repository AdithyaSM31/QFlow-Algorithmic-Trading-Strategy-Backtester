"""Market data routes — query OHLCV data and available symbols."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.market_data import OHLCVBar, SymbolInfo

router = APIRouter()


@router.get("/symbols", response_model=list[SymbolInfo])
async def list_symbols(db: AsyncSession = Depends(get_db)):
    """List all available symbols with date range and bar count."""
    result = await db.execute(text("""
        SELECT symbol,
               MIN(timestamp) AS first_date,
               MAX(timestamp) AS last_date,
               COUNT(*) AS total_bars
        FROM market_data
        GROUP BY symbol
        ORDER BY symbol
    """))
    rows = result.mappings().all()
    return [SymbolInfo(**row) for row in rows]


@router.post("/ingest", status_code=202)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
):
    """Trigger background market data ingestion."""
    def run_ingest():
        import os
        from sqlalchemy import create_engine
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))
        from scripts.ingest_data import ingest_symbol, DEFAULT_SYMBOLS
        from app.config import get_settings
        
        settings = get_settings()
        engine = create_engine(settings.DATABASE_URL_SYNC)
        for sym in DEFAULT_SYMBOLS:
            try:
                ingest_symbol(engine, sym, "5y")
            except Exception as e:
                print(f"Failed to ingest {sym}: {e}")

    background_tasks.add_task(run_ingest)
    return {"status": "Ingestion started in background"}


@router.get("/{symbol}", response_model=list[OHLCVBar])
async def get_market_data(
    symbol: str,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    limit: int = Query(1000, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Query OHLCV data for a symbol."""
    query = """
        SELECT timestamp, symbol, open, high, low, close, volume, adj_close
        FROM market_data
        WHERE symbol = :symbol
    """
    params = {"symbol": symbol.upper()}

    if start_date:
        query += " AND timestamp >= :start"
        params["start"] = start_date
    if end_date:
        query += " AND timestamp <= :end"
        params["end"] = end_date

    query += " ORDER BY timestamp ASC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

    return [OHLCVBar(**row) for row in rows]
