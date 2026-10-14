"""Ingest Twelve Data websocket prices into Tiger Cloud.

Follows the Tiger Data tutorial, with two practical additions:
ticks are stored as timezone-aware UTC, and a partial batch is flushed
on each heartbeat so a slow feed still lands in the database.
"""

import os
import time
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values
from twelvedata import TDClient

load_dotenv()

SYMBOLS = ["BTC/USD", "ETH/USD", "MSFT", "AAPL"]
ASSETS = [
    ("BTC/USD", "Bitcoin"),
    ("ETH/USD", "Ethereum"),
    ("MSFT", "Microsoft"),
    ("AAPL", "Apple"),
]


class WebsocketPipeline:
    DB_TABLE = "crypto_ticks"
    DB_COLUMNS = ["time", "symbol", "price", "day_volume"]
    MAX_BATCH_SIZE = 100

    def __init__(self, conn):
        self.conn = conn
        self.current_batch = []
        self.insert_counter = 0
        self._ensure_assets()

    def _ensure_assets(self):
        with self.conn.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO crypto_assets (symbol, name)
                VALUES %s
                ON CONFLICT (symbol) DO NOTHING
                """,
                ASSETS,
            )
        self.conn.commit()

    def _insert_values(self, data):
        if not data or self.conn is None:
            return
        with self.conn.cursor() as cursor:
            sql = f"""
            INSERT INTO {self.DB_TABLE} ({",".join(self.DB_COLUMNS)})
            VALUES %s
            """
            execute_values(cursor, sql, data)
        self.conn.commit()
        self.insert_counter += 1
        print(f"Batch insert #{self.insert_counter} ({len(data)} rows)")

    def _flush(self):
        if not self.current_batch:
            return
        batch = self.current_batch
        self.current_batch = []
        self._insert_values(batch)

    def _on_event(self, event):
        if event.get("event") != "price":
            print(event)
            return

        timestamp = datetime.fromtimestamp(event["timestamp"], tz=timezone.utc)
        self.current_batch.append(
            (
                timestamp,
                event["symbol"],
                event["price"],
                event.get("day_volume"),
            )
        )
        print(f"Current batch size: {len(self.current_batch)}")

        if len(self.current_batch) >= self.MAX_BATCH_SIZE:
            self._flush()

    def start(self, symbols):
        td = TDClient(apikey=os.environ["TWELVE_DATA_API_KEY"])
        ws = td.websocket(on_event=self._on_event, log_level="info")
        ws.subscribe(symbols)
        ws.connect()
        while True:
            ws.heartbeat()
            # Heartbeat is every 10s. Flush whatever has arrived so the
            # dashboard is not stuck waiting for a full 100-tick batch.
            self._flush()
            time.sleep(10)


def connect():
    return psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.environ["PGPORT"],
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require"),
    )


if __name__ == "__main__":
    conn = connect()
    WebsocketPipeline(conn).start(symbols=SYMBOLS)
