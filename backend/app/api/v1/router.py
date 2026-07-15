"""API v1 Router — aggregates all v1 route modules."""

from fastapi import APIRouter
from app.api.v1 import auth, strategies, backtests, market_data, websockets

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_v1_router.include_router(strategies.router, prefix="/strategies", tags=["Strategies"])
api_v1_router.include_router(backtests.router, prefix="/backtests", tags=["Backtests"])
api_v1_router.include_router(market_data.router, prefix="/market-data", tags=["Market Data"])
api_v1_router.include_router(websockets.router, prefix="/ws", tags=["WebSockets"])
