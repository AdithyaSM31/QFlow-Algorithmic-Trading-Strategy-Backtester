"""
QFlow — FastAPI Application Factory
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
        allow_origins=[
            "http://localhost:3000", 
            "http://localhost:5173", 
            "https://q-flow-neon.vercel.app",
            "http://localhost",
            "https://localhost",
            "capacitor://localhost"
        ],
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

    @application.get("/api/v1/setup-db", tags=["Debug"])
    async def setup_db_endpoint():
        import os
        import psycopg2
        from pathlib import Path
        db_url = os.getenv("DATABASE_URL_SYNC", settings.DATABASE_URL_SYNC)
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            cursor = conn.cursor()
            
            sql_file = Path(__file__).parent.parent / "scripts" / "init_db.sql"
            with open(sql_file, "r") as f:
                sql = f.read()
                
            cursor.execute(sql)
            cursor.close()
            conn.close()
            return {"status": "success", "msg": "Database initialized."}
        except Exception as e:
            return {"status": "error", "msg": str(e), "db_url_starts_with": db_url[:15] if db_url else None}

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        origin = request.headers.get("origin")
        headers = {}
        if origin in [
            "http://localhost:3000", 
            "http://localhost:5173", 
            "https://q-flow-neon.vercel.app",
            "http://localhost",
            "https://localhost",
            "capacitor://localhost"
        ]:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "msg": str(exc)},
            headers=headers
        )

    return application


app = create_app()
