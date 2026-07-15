-- ============================================================
-- QFlow (QuantFlow) — TimescaleDB Initialization
-- Creates hypertables, continuous aggregates, and indexes
-- for high-performance time-series financial data storage.
-- ============================================================

-- Enable TimescaleDB extension (fails gracefully if not available on Render Free Postgres)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
        CREATE EXTENSION IF NOT EXISTS timescaledb;
    ELSE
        RAISE NOTICE 'TimescaleDB not available. Using standard PostgreSQL tables.';
    END IF;
END
$$;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    username        TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- MARKET DATA (Hypertable — auto-partitioned by time)
-- ============================================================
CREATE TABLE IF NOT EXISTS market_data (
    timestamp   TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      BIGINT NOT NULL,
    adj_close   DOUBLE PRECISION,
    UNIQUE (symbol, timestamp)
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('market_data', 'timestamp', if_not_exists => TRUE);
    END IF;
END
$$;

-- Composite index: symbol + time DESC for fast range queries
CREATE INDEX IF NOT EXISTS idx_market_symbol_time
    ON market_data (symbol, timestamp DESC);

-- ============================================================
-- CONTINUOUS AGGREGATES — pre-computed OHLCV candles
-- Materializes 1-day candles from intraday data automatically.
-- For daily-only data ingestion, this still works correctly.
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        EXECUTE '
        CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1d
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket(''1 day'', timestamp)   AS bucket,
            symbol,
            first(open, timestamp)            AS open,
            max(high)                         AS high,
            min(low)                          AS low,
            last(close, timestamp)            AS close,
            sum(volume)                       AS volume,
            last(adj_close, timestamp)        AS adj_close
        FROM market_data
        GROUP BY bucket, symbol
        WITH NO DATA;';

        PERFORM add_continuous_aggregate_policy('candles_1d',
            start_offset    => INTERVAL '1 year',
            end_offset      => INTERVAL '1 day',
            schedule_interval => INTERVAL '1 day',
            if_not_exists   => TRUE
        );
    END IF;
END
$$;

-- ============================================================
-- CONTINUOUS AGGREGATE: Weekly candles (built on raw data)
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        EXECUTE '
        CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1w
        WITH (timescaledb.continuous) AS
        SELECT
            time_bucket(''1 week'', timestamp)  AS bucket,
            symbol,
            first(open, timestamp)            AS open,
            max(high)                         AS high,
            min(low)                          AS low,
            last(close, timestamp)            AS close,
            sum(volume)                       AS volume,
            last(adj_close, timestamp)        AS adj_close
        FROM market_data
        GROUP BY bucket, symbol
        WITH NO DATA;';

        PERFORM add_continuous_aggregate_policy('candles_1w',
            start_offset    => INTERVAL '2 years',
            end_offset      => INTERVAL '1 week',
            schedule_interval => INTERVAL '1 week',
            if_not_exists   => TRUE
        );
    END IF;
END
$$;

-- ============================================================
-- STRATEGIES
-- ============================================================
CREATE TABLE IF NOT EXISTS strategies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL,
    parameters      JSONB NOT NULL DEFAULT '{}',
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_strategies_user ON strategies (user_id);

-- ============================================================
-- BACKTESTS
-- ============================================================
CREATE TABLE IF NOT EXISTS backtests (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    strategy_id       UUID REFERENCES strategies(id) ON DELETE CASCADE,
    user_id           UUID REFERENCES users(id) ON DELETE CASCADE,
    status            TEXT DEFAULT 'PENDING',
    symbols           TEXT[] NOT NULL,
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    initial_capital   DOUBLE PRECISION DEFAULT 100000,
    slippage_bps      DOUBLE PRECISION DEFAULT 5.0,
    commission_pct    DOUBLE PRECISION DEFAULT 0.1,
    celery_task_id    TEXT,
    progress          DOUBLE PRECISION DEFAULT 0.0,
    submitted_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    error_message     TEXT
);

CREATE INDEX IF NOT EXISTS idx_backtests_user ON backtests (user_id);
CREATE INDEX IF NOT EXISTS idx_backtests_status ON backtests (status);

-- ============================================================
-- BACKTEST RESULTS (Hypertable — equity curve time-series)
-- ============================================================
CREATE TABLE IF NOT EXISTS backtest_results (
    backtest_id       UUID NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp         TIMESTAMPTZ NOT NULL,
    portfolio_value   DOUBLE PRECISION NOT NULL,
    cash              DOUBLE PRECISION NOT NULL,
    positions_value   DOUBLE PRECISION NOT NULL,
    positions         JSONB DEFAULT '{}',
    daily_return      DOUBLE PRECISION DEFAULT 0.0,
    cumulative_return DOUBLE PRECISION DEFAULT 0.0
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('backtest_results', 'timestamp', if_not_exists => TRUE);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_results_backtest
    ON backtest_results (backtest_id, timestamp DESC);

-- ============================================================
-- TRADES LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_id     UUID NOT NULL REFERENCES backtests(id) ON DELETE CASCADE,
    timestamp       TIMESTAMPTZ NOT NULL,
    symbol          TEXT NOT NULL,
    side            TEXT NOT NULL,
    quantity        INTEGER NOT NULL,
    price           DOUBLE PRECISION NOT NULL,
    fill_price      DOUBLE PRECISION NOT NULL,
    slippage        DOUBLE PRECISION DEFAULT 0.0,
    commission      DOUBLE PRECISION DEFAULT 0.0,
    pnl             DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_trades_backtest ON trades (backtest_id, timestamp);

-- ============================================================
-- BACKTEST ANALYTICS (computed summary metrics)
-- ============================================================
CREATE TABLE IF NOT EXISTS backtest_analytics (
    backtest_id         UUID PRIMARY KEY REFERENCES backtests(id) ON DELETE CASCADE,
    total_return        DOUBLE PRECISION,
    annualized_return   DOUBLE PRECISION,
    sharpe_ratio        DOUBLE PRECISION,
    sortino_ratio       DOUBLE PRECISION,
    max_drawdown        DOUBLE PRECISION,
    max_drawdown_duration_days INTEGER,
    calmar_ratio        DOUBLE PRECISION,
    win_rate            DOUBLE PRECISION,
    profit_factor       DOUBLE PRECISION,
    total_trades        INTEGER,
    avg_trade_pnl       DOUBLE PRECISION,
    best_trade          DOUBLE PRECISION,
    worst_trade         DOUBLE PRECISION,
    volatility          DOUBLE PRECISION,
    beta                DOUBLE PRECISION,
    alpha               DOUBLE PRECISION,
    avg_win             DOUBLE PRECISION,
    avg_loss            DOUBLE PRECISION,
    expectancy          DOUBLE PRECISION
);

-- ============================================================
-- COMPRESSION POLICY — compress old raw market data
-- Saves 90%+ storage on historical tick data
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        EXECUTE '
        ALTER TABLE market_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = ''symbol'',
            timescaledb.compress_orderby = ''timestamp DESC''
        );';

        PERFORM add_compression_policy('market_data', INTERVAL '30 days', if_not_exists => TRUE);
    END IF;
END
$$;
