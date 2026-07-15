"""Market data routes — query OHLCV data and available symbols."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/{symbol}", response_model=list[OHLCVBar])
async def get_market_data(
    symbol: str,
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    timeframe: str = Query("1d", regex="^(1d|1w)$"),
    limit: int = Query(1000, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Query OHLCV data for a symbol. Supports daily and weekly timeframes."""
    # Choose source: continuous aggregate or raw table
    if timeframe == "1w":
        table = "candles_1w"
        ts_col = "bucket"
    else:
        table = "market_data"
        ts_col = "timestamp"

    query = f"""
        SELECT {ts_col} AS timestamp, symbol, open, high, low, close, volume, adj_close
        FROM {table}
        WHERE symbol = :symbol
    """
    params = {"symbol": symbol.upper()}

    if start_date:
        query += f" AND {ts_col} >= :start"
        params["start"] = start_date
    if end_date:
        query += f" AND {ts_col} <= :end"
        params["end"] = end_date

    query += f" ORDER BY {ts_col} ASC LIMIT :limit"
    params["limit"] = limit

    result = await db.execute(text(query), params)
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

    return [OHLCVBar(**row) for row in rows]
