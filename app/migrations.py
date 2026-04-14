from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

from app.db import get_engine

MIGRATION_SQL = [
    """
    CREATE TABLE IF NOT EXISTS trade_calendar (
      cal_date DATE PRIMARY KEY,
      is_open BOOLEAN NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_basic (
      ts_code TEXT PRIMARY KEY,
      symbol TEXT,
      name TEXT,
      area TEXT,
      industry TEXT,
      market TEXT,
      exchange TEXT,
      list_status TEXT,
      list_date DATE,
      delist_date DATE,
      is_hs TEXT,
      updated_at TIMESTAMPTZ
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_daily (
      ts_code TEXT,
      trade_date DATE,
      open NUMERIC,
      high NUMERIC,
      low NUMERIC,
      close NUMERIC,
      pre_close NUMERIC,
      change NUMERIC,
      pct_chg NUMERIC,
      vol NUMERIC,
      amount NUMERIC,
      turnover_rate NUMERIC,
      turnover_rate_f NUMERIC,
      volume_ratio NUMERIC,
      pe NUMERIC,
      pe_ttm NUMERIC,
      pb NUMERIC,
      ps NUMERIC,
      ps_ttm NUMERIC,
      dv_ratio NUMERIC,
      dv_ttm NUMERIC,
      total_share NUMERIC,
      float_share NUMERIC,
      free_share NUMERIC,
      total_mv NUMERIC,
      circ_mv NUMERIC,
      PRIMARY KEY (ts_code, trade_date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS stock_adj_factor (
      ts_code TEXT,
      trade_date DATE,
      adj_factor NUMERIC NOT NULL,
      PRIMARY KEY (ts_code, trade_date)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_state (
      trade_date DATE PRIMARY KEY,
      prices_synced BOOLEAN DEFAULT FALSE,
      adj_synced BOOLEAN DEFAULT FALSE,
      completed_at TIMESTAMPTZ
    );
    """,
]


def run_migrations(engine: Engine | None = None) -> None:
    db_engine = engine or get_engine()
    with db_engine.begin() as connection:
        for sql in MIGRATION_SQL:
            connection.execute(text(sql))
