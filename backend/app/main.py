"""
QFlow — FastAPI Application Factory
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.v1.router import api_v1_router

settings = get_settings()


def create_app() -> FastAPI:
    application = FastAPI(
        title="QFlow — Algorithmic Trading Backtester",
        description=(
            "Production-grade backtesting platform for defining trading strategies "
            "(MA crossover, RSI, Bollinger Bands, custom ML signals), "
            "submitting backtests as async jobs, and getting PnL analytics."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — allow frontend origin
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 routes
    application.include_router(api_v1_router, prefix="/api/v1")

    @application.get("/health", tags=["Health"])
    @application.get("/api/v1/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "app": settings.APP_NAME}

    return application


app = create_app()
