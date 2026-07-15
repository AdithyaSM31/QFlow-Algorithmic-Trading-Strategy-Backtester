# QFlow — Algorithmic Trading Strategy Backtester

<p align="center">
  <img src="frontend/assets/icon.jpg" width="150" alt="QFlow Logo">
</p>
> Production-grade backtesting platform where users define trading strategies (MA crossover, RSI, Bollinger Bands, custom ML signals), submit backtests as async jobs, and get institutional-grade PnL analytics.

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![TimescaleDB](https://img.shields.io/badge/TimescaleDB-FDB515?style=flat-square&logo=timescale&logoColor=black)
![Celery](https://img.shields.io/badge/Celery-37814A?style=flat-square&logo=celery&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.12-3776AB?style=flat-square&logo=python&logoColor=white)

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     React Dashboard                        │
│  (Strategy Builder · Backtest Submit · Analytics Viewer)   │
└──────────────────────────┬─────────────────────────────────┘
                           │ HTTP / WebSocket
┌──────────────────────────▼─────────────────────────────────┐
│                     FastAPI Backend                         │
│  (REST API · JWT Auth · Pydantic Validation · WebSocket)   │
└──────┬──────────────────────────────────────┬──────────────┘
       │ Enqueue                              │ Read/Write
┌──────▼──────┐                    ┌──────────▼──────────────┐
│    Redis    │◄──── Pub/Sub ────► │      TimescaleDB        │
│  (Broker)   │                    │  (Hypertables + Cont.   │
└──────┬──────┘                    │   Aggregates + OHLCV)   │
       │ Dispatch                  └─────────────────────────┘
┌──────▼───────────────────────┐
│       Celery Workers         │
│  ┌─────────┐  ┌────────────┐ │
│  │ Fast Q  │  │  Slow Q    │ │
│  │ <1yr    │  │  Multi-yr  │ │
│  │ 2 conc  │  │  1 conc    │ │
│  └────┬────┘  └─────┬──────┘ │
│       └──────┬──────┘        │
│     Event-Driven Engine      │
│  DataHandler → Strategy →    │
│  Portfolio → Execution →     │
│  Analytics                   │
└──────────────────────────────┘
```

## Key Features

- **Event-Driven Backtest Engine** — Point-in-time data access prevents look-ahead bias
- **Async Job Processing** — Celery workers with priority queues (fast/slow lanes)
- **TimescaleDB** — Hypertable partitioning + continuous aggregates for OHLCV candles
- **Execution Realism** — Configurable slippage (bps) + commission modeling
- **19 Analytics Metrics** — Sharpe, Sortino, Max Drawdown, Calmar, Win Rate, Profit Factor, Alpha, Beta
- **Built-in Strategies** — MA Crossover, RSI Mean Reversion, Bollinger Bands
- **ML-Ready** — Walk-forward validated ML signal pipeline (Phase 5)
- **Interactive Dashboard** — Recharts equity curves, drawdown charts, trade log

## 📱 Mobile App (Native Android)
QFlow is now fully transformed from a web-based engine into a premium, native-feeling mobile application using Ionic Capacitor (v1.0).
- **Responsive UI/UX Overhaul**: Bottom navigation bar, intelligent grid stacking for complex strategy builders, and mobile-optimized auth flows.
- **Native Experience**: Safe-area optimizations for edge-to-edge displays (camera notches, home indicators) and a bespoke Android launcher icon and splash screen.
- **Production Architecture**: Connected seamlessly to the live Render-hosted FastAPI backend with secure CORS integration.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)

### 1. Start the Stack
```bash
docker compose up -d
```

This starts: API (8000), TimescaleDB (5432), Redis (6379), Fast Worker, Slow Worker, Flower (5555)

### 2. Ingest Market Data
```bash
docker compose exec api python -m scripts.ingest_data
```

Downloads 10 years of OHLCV data for 14 symbols from Yahoo Finance.

### 3. Start Frontend (Development)
```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App
- **Dashboard**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
- **Flower (Task Monitor)**: http://localhost:5555

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI | Async-native, auto OpenAPI docs, Pydantic validation |
| Task Queue | Celery + Redis | Industry-standard async jobs; Redis doubles as pub/sub |
| Database | TimescaleDB | Time-series optimized PostgreSQL — hypertables + continuous aggregates |
| ORM | SQLAlchemy 2.0 | Async support, mature ecosystem |
| Frontend | React + Recharts | Interactive financial data visualization |
| Auth | JWT (python-jose) | Stateless, scalable authentication |
| Monitoring | Flower | Real-time Celery task dashboard |

## Project Structure

```
qflow/
├── docker-compose.yml          # Full stack orchestration
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app factory
│   │   ├── config.py           # Pydantic Settings
│   │   ├── database.py         # Async SQLAlchemy
│   │   ├── api/v1/             # REST endpoints
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic validation
│   │   ├── engine/             # ⭐ Backtest engine
│   │   │   ├── event.py        # Event types
│   │   │   ├── data_handler.py # Point-in-time feed
│   │   │   ├── strategy.py     # Strategy base + built-ins
│   │   │   ├── portfolio.py    # Position tracker
│   │   │   ├── execution.py    # Slippage + commission sim
│   │   │   ├── analytics.py    # Risk metrics calculator
│   │   │   └── runner.py       # Main event loop
│   │   └── workers/            # Celery tasks
│   ├── scripts/
│   │   ├── init_db.sql         # TimescaleDB schema
│   │   └── ingest_data.py      # Yahoo Finance loader
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── pages/              # Dashboard, Strategies, etc.
    │   ├── components/         # Sidebar, Charts
    │   └── api.js              # Axios API client
    └── Dockerfile
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/strategies/` | List strategies |
| POST | `/api/v1/strategies/` | Create strategy |
| POST | `/api/v1/backtests/` | Submit backtest → async job |
| GET | `/api/v1/backtests/{id}` | Get status + analytics |
| GET | `/api/v1/backtests/{id}/equity` | Equity curve data |
| GET | `/api/v1/backtests/{id}/trades` | Trade log |
| GET | `/api/v1/market-data/symbols` | Available symbols |

## License

MIT
