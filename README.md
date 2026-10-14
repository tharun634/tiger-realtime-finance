# Real-time financial ingest into Tiger Cloud

Python websocket pipeline that follows the [Tiger Data tutorial](https://www.tigerdata.com/docs/learn/tutorials/ingest-real-time-financial-data): Twelve Data prices land in a TimescaleDB hypertable, continuous aggregates build OHLCV candles, and a self-hosted Grafana dashboard charts them.

Service: Tiger Cloud `db-60430` (`vg9jkjuima`, `us-east-1`, DEV).

## Layout

- `websocket_test.py` subscribes to `BTC/USD`, `ETH/USD`, `MSFT`, and `AAPL`, batches ticks, and inserts them into `crypto_ticks`.
- `sql/001_schema.sql` creates the hypertable, `crypto_assets`, a daily continuous aggregate (`one_day_candle`), and a one-minute aggregate (`one_minute_candle`) so a short live session still draws candles.
- Grafana OSS runs locally and is provisioned from `grafana/`.

## Setup

Python 3.13.1 via pyenv, virtualenv in `.venv`:

```powershell
pyenv local 3.13.1
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Fill `.env` with the Twelve Data API key and the Tiger Cloud connection. `.env` is gitignored.

The schema is already applied on `db-60430`. To reapply it:

```powershell
python apply_schema.py
```

Continuous aggregates are created with autocommit, because PostgreSQL rejects `CREATE MATERIALIZED VIEW ... WITH DATA` inside a transaction. The policy statements are not idempotent; skip them if the policies already exist.

## Run the pipeline

```powershell
.\.venv\Scripts\Activate.ps1
python websocket_test.py
```

Crypto pairs trade continuously. `MSFT` and `AAPL` only tick while the US cash session is open. Heartbeats flush the in-memory batch every 10 seconds, and a full batch of 100 rows flushes immediately.

On the free Twelve Data websocket plan, the first connection accepted `BTC/USD` and `AAPL` and rejected `ETH/USD` and `MSFT` (`subscribe-status: warning`). The script still requests all four symbols from the tutorial. A higher plan is what adds the other two.

## Grafana

Grafana OSS 13.2.4 is unpacked under `%LOCALAPPDATA%\grafana-oss` (the Windows binary is `bin\grafana.exe`). From this folder:

```powershell
.\start-grafana.ps1
```

Open http://localhost:3000 and sign in with `admin` / `admin`. The **Finance / Tiger Cloud OHLCV** dashboard is provisioned automatically. The PostgreSQL data source uses TLS (`sslmode=require`) and has TimescaleDB enabled.
