from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TradeCalendar(Base):
    __tablename__ = "trade_calendar"

    cal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False)


class StockBasic(Base):
    __tablename__ = "stock_basic"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String)
    name: Mapped[str | None] = mapped_column(String)
    area: Mapped[str | None] = mapped_column(String)
    industry: Mapped[str | None] = mapped_column(String)
    market: Mapped[str | None] = mapped_column(String)
    exchange: Mapped[str | None] = mapped_column(String)
    list_status: Mapped[str | None] = mapped_column(String)
    list_date: Mapped[date | None] = mapped_column(Date)
    delist_date: Mapped[date | None] = mapped_column(Date)
    is_hs: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StockDaily(Base):
    __tablename__ = "stock_daily"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric)
    high: Mapped[float | None] = mapped_column(Numeric)
    low: Mapped[float | None] = mapped_column(Numeric)
    close: Mapped[float | None] = mapped_column(Numeric)
    pre_close: Mapped[float | None] = mapped_column(Numeric)
    change: Mapped[float | None] = mapped_column(Numeric)
    pct_chg: Mapped[float | None] = mapped_column(Numeric)
    vol: Mapped[float | None] = mapped_column(Numeric)
    amount: Mapped[float | None] = mapped_column(Numeric)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric)
    turnover_rate_f: Mapped[float | None] = mapped_column(Numeric)
    volume_ratio: Mapped[float | None] = mapped_column(Numeric)
    pe: Mapped[float | None] = mapped_column(Numeric)
    pe_ttm: Mapped[float | None] = mapped_column(Numeric)
    pb: Mapped[float | None] = mapped_column(Numeric)
    ps: Mapped[float | None] = mapped_column(Numeric)
    ps_ttm: Mapped[float | None] = mapped_column(Numeric)
    dv_ratio: Mapped[float | None] = mapped_column(Numeric)
    dv_ttm: Mapped[float | None] = mapped_column(Numeric)
    total_share: Mapped[float | None] = mapped_column(Numeric)
    float_share: Mapped[float | None] = mapped_column(Numeric)
    free_share: Mapped[float | None] = mapped_column(Numeric)
    total_mv: Mapped[float | None] = mapped_column(Numeric)
    circ_mv: Mapped[float | None] = mapped_column(Numeric)


class StockAdjFactor(Base):
    __tablename__ = "stock_adj_factor"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    adj_factor: Mapped[float] = mapped_column(Numeric, nullable=False)


class SyncState(Base):
    __tablename__ = "sync_state"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    prices_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    adj_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
