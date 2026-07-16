<p align="center">
  <img src="frontend/assets/icon.jpg" width="220" alt="QFlow Logo" style="border-radius: 20px;">
</p>

<h1 align="center">QFlow — Algorithmic Trading Strategy Backtester</h1>

<p align="center">
  <em>Production-grade backtesting platform where users define trading strategies (MA crossover, RSI, Bollinger Bands), submit backtests as async jobs, and get institutional-grade PnL analytics.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/TimescaleDB-FDB515?style=for-the-badge&logo=timescale&logoColor=black" alt="TimescaleDB">
  <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery">
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React">
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/Python_3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/Capacitor-119EFF?style=for-the-badge&logo=capacitor&logoColor=white" alt="Capacitor">
</p>

<p align="center">
  <a href="https://q-flow-neon.vercel.app">🌐 Live Demo</a> &nbsp;·&nbsp;
  <a href="https://github.com/AdithyaSM31/QFlow-Algorithmic-Trading-Strategy-Backtester/releases">📦 Android APK</a> &nbsp;·&nbsp;
  <a href="https://qflow-api-w980.onrender.com/docs">📄 API Docs</a>
</p>

---

## 🏗️ Architecture

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

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Event-Driven Engine** | Point-in-time data access prevents look-ahead bias |
| ⚡ **Async Job Processing** | Celery workers with fast/slow priority queues |
| 📊 **TimescaleDB** | Hypertable partitioning + continuous aggregates for OHLCV candles |
| 🎯 **Execution Realism** | Configurable slippage (bps) + commission modeling |
| 📈 **19 Risk Metrics** | Sharpe, Sortino, Max Drawdown, Calmar, Win Rate, Profit Factor, Alpha, Beta |
| 🧠 **Built-in Strategies** | MA Crossover, RSI Mean Reversion, Bollinger Bands |
| 📱 **Native Android App** | Packaged with Ionic Capacitor, responsive mobile UI |
| 🖥️ **Interactive Dashboard** | Recharts equity curves, drawdown charts, trade log |

## 📱 Mobile App (Native Android)

QFlow is available as a native Android application built with Ionic Capacitor.

- **Bottom Navigation** — Reimagined sidebar as a touch-friendly bottom bar with glassmorphism
- **Responsive Layouts** — Strategy builders and metric grids stack cleanly on mobile viewports
- **Safe-Area Support** — Edge-to-edge display with proper notch and status bar handling
- **Custom Branding** — Native launcher icon and splash screen generated from project assets

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for frontend development)

### 1. Start the Stack
```bash
docker compose up -d
```
> Starts: API (8000), TimescaleDB (5432), Redis (6379), Fast Worker, Slow Worker, Flower (5555)

### 2. Ingest Market Data
```bash
docker compose exec api python -m scripts.ingest_data
```
> Downloads 10 years of OHLCV data for 14 symbols from Yahoo Finance.

### 3. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

### 4. Open the App
| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |
| Flower (Task Monitor) | http://localhost:5555 |

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| API | FastAPI | Async-native, auto OpenAPI docs, Pydantic validation |
| Task Queue | Celery + Redis | Industry-standard async jobs; Redis doubles as pub/sub |
| Database | TimescaleDB | Time-series optimized PostgreSQL — hypertables + continuous aggregates |
| ORM | SQLAlchemy 2.0 | Async support, mature ecosystem |
| Frontend | React + Recharts | Interactive financial data visualization |
| Auth | JWT (python-jose) | Stateless, scalable authentication |
| Mobile | Capacitor | Native Android wrapper for the React frontend |
| Monitoring | Flower | Real-time Celery task dashboard |

## 📁 Project Structure

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
    ├── android/                # Capacitor native project
    └── Dockerfile
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | User registration |
| `POST` | `/api/v1/auth/login` | JWT login |
| `GET` | `/api/v1/strategies/` | List strategies |
| `POST` | `/api/v1/strategies/` | Create strategy |
| `POST` | `/api/v1/backtests/` | Submit backtest → async job |
| `GET` | `/api/v1/backtests/{id}` | Get status + analytics |
| `GET` | `/api/v1/backtests/{id}/equity` | Equity curve data |
| `GET` | `/api/v1/backtests/{id}/trades` | Trade log |
| `GET` | `/api/v1/market-data/symbols` | Available symbols |

## 📄 License

MIT
