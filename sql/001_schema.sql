-- Real-time Twelve Data ticks. Partition on time, segment by symbol
-- (the filter used by every candle query). Columnstore is enabled by the
-- hypertable defaults on Tiger Cloud (TimescaleDB 2.30).

CREATE TABLE IF NOT EXISTS crypto_ticks (
    "time" TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION,
    day_volume NUMERIC
) WITH (
    tsdb.hypertable,
    tsdb.partition_column = 'time',
    tsdb.segmentby = 'symbol',
    tsdb.orderby = 'time DESC'
);

CREATE INDEX IF NOT EXISTS idx_crypto_ticks_symbol_time
    ON crypto_ticks (symbol, "time" DESC);

CREATE TABLE IF NOT EXISTS crypto_assets (
    symbol TEXT UNIQUE,
    "name" TEXT
);

INSERT INTO crypto_assets (symbol, "name") VALUES
    ('BTC/USD', 'Bitcoin'),
    ('ETH/USD', 'Ethereum'),
    ('MSFT', 'Microsoft'),
    ('AAPL', 'Apple')
ON CONFLICT (symbol) DO NOTHING;

-- Tutorial aggregate: one OHLCV candle per symbol per day.
CREATE MATERIALIZED VIEW IF NOT EXISTS one_day_candle
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', "time") AS bucket,
    symbol,
    FIRST(price, "time") AS "open",
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, "time") AS "close",
    LAST(day_volume, "time") AS day_volume
FROM crypto_ticks
GROUP BY bucket, symbol;

SELECT add_continuous_aggregate_policy(
    'one_day_candle',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day'
);

-- The daily policy excludes the current day. Real-time aggregation unions
-- the open bucket from raw ticks so Grafana can show today's candle.
ALTER MATERIALIZED VIEW one_day_candle SET (timescaledb.materialized_only = false);

-- A few minutes of ingest only fills one daily bucket. Minute candles make
-- the live chart readable during the same session.
CREATE MATERIALIZED VIEW IF NOT EXISTS one_minute_candle
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', "time") AS bucket,
    symbol,
    FIRST(price, "time") AS "open",
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, "time") AS "close",
    LAST(day_volume, "time") AS day_volume
FROM crypto_ticks
GROUP BY bucket, symbol;

SELECT add_continuous_aggregate_policy(
    'one_minute_candle',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
);

ALTER MATERIALIZED VIEW one_minute_candle SET (timescaledb.materialized_only = false);
