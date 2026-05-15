from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import StockAdjFactor, StockDaily, SyncState, TradeCalendar
from app.db.session import get_session_factory
from app.sync.aux_bootstrap import bootstrap_aux, maybe_refresh_aux
from app.sync.bootstrap import (
    bootstrap_trade_calendar,
    maybe_refresh_stock_basic,
)
from app.sync.fina_bootstrap import (
    bootstrap_financials,
    maybe_refresh_financials,
)
from app.sync.index_bootstrap import (
    bootstrap_index_members,
    maybe_refresh_index_members,
)
from app.sync.tushare_client import TushareClient

logger = logging.getLogger(__name__)

_sync_lock = asyncio.Lock()
_sync_runtime = {"running": False, "job_id": None}


def get_sync_lock() -> asyncio.Lock:
    return _sync_lock


def get_runtime_state() -> dict[str, object | None]:
    return _sync_runtime


def _cst_today() -> date:
    return datetime.now(ZoneInfo("Asia/Shanghai")).date()


def get_missing_dates(session: Session) -> list[date]:
    today = _cst_today()
    query = (
        select(TradeCalendar.cal_date)
        .outerjoin(SyncState, SyncState.trade_date == TradeCalendar.cal_date)
        .where(
            and_(
                TradeCalendar.is_open.is_(True),
                TradeCalendar.cal_date < today,
                or_(
                    SyncState.trade_date.is_(None),
                    SyncState.prices_synced.is_(False),
                    SyncState.adj_synced.is_(False),
                ),
            )
        )
        .order_by(TradeCalendar.cal_date.asc())
    )
    return list(session.execute(query).scalars().all())


def _upsert_sync_state(session: Session, trade_date: date, **values: object) -> None:
    stmt = insert(SyncState).values(trade_date=trade_date, **values)
    stmt = stmt.on_conflict_do_update(index_elements=[SyncState.trade_date], set_=values)
    session.execute(stmt)
    session.commit()


def sync_prices_for_date(session: Session, client: TushareClient, trade_date: date) -> None:
    try:
        daily_df = client.fetch_daily(trade_date)
    except RuntimeError:
        _upsert_sync_state(session, trade_date, prices_synced=True)
        return
    try:
        basic_df = client.fetch_daily_basic(trade_date)
        basic_by_code = {row["ts_code"]: row for row in basic_df.to_dict(orient="records")}
    except RuntimeError:
        basic_by_code = {}
    rows: list[dict[str, object | None]] = []
    for record in daily_df.to_dict(orient="records"):
        basic = basic_by_code.get(record["ts_code"], {})
        rows.append(
            {
                "ts_code": record.get("ts_code"),
                "trade_date": datetime.strptime(record["trade_date"], "%Y%m%d").date(),
                "open": record.get("open"),
                "high": record.get("high"),
                "low": record.get("low"),
                "close": record.get("close"),
                "pre_close": record.get("pre_close"),
                "change": record.get("change"),
                "pct_chg": record.get("pct_chg"),
                "vol": record.get("vol"),
                "amount": record.get("amount"),
                "turnover_rate": basic.get("turnover_rate"),
                "turnover_rate_f": basic.get("turnover_rate_f"),
                "volume_ratio": basic.get("volume_ratio"),
                "pe": basic.get("pe"),
                "pe_ttm": basic.get("pe_ttm"),
                "pb": basic.get("pb"),
                "ps": basic.get("ps"),
                "ps_ttm": basic.get("ps_ttm"),
                "dv_ratio": basic.get("dv_ratio"),
                "dv_ttm": basic.get("dv_ttm"),
                "total_share": basic.get("total_share"),
                "float_share": basic.get("float_share"),
                "free_share": basic.get("free_share"),
                "total_mv": basic.get("total_mv"),
                "circ_mv": basic.get("circ_mv"),
            }
        )
    if rows:
        stmt = insert(StockDaily).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[StockDaily.ts_code, StockDaily.trade_date],
            set_={k: stmt.excluded[k] for k in rows[0].keys() if k not in {"ts_code", "trade_date"}},
        )
        session.execute(stmt)
        session.commit()
    _upsert_sync_state(session, trade_date, prices_synced=True)


def sync_adj_factor_for_date(session: Session, client: TushareClient, trade_date: date) -> None:
    try:
        adj_df = client.fetch_adj_factor(trade_date)
    except RuntimeError:
        _upsert_sync_state(session, trade_date, adj_synced=True, completed_at=datetime.now(ZoneInfo("Asia/Shanghai")))
        return
    rows = [
        {
            "ts_code": item["ts_code"],
            "trade_date": datetime.strptime(item["trade_date"], "%Y%m%d").date(),
            "adj_factor": item["adj_factor"],
        }
        for item in adj_df.to_dict(orient="records")
    ]
    if rows:
        stmt = insert(StockAdjFactor).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[StockAdjFactor.ts_code, StockAdjFactor.trade_date],
            set_={"adj_factor": stmt.excluded.adj_factor},
        )
        session.execute(stmt)
        session.commit()
    _upsert_sync_state(session, trade_date, adj_synced=True, completed_at=datetime.now(ZoneInfo("Asia/Shanghai")))


def _sync_date(session: Session, client: TushareClient, trade_date: date) -> None:
    current = session.get(SyncState, trade_date)
    if not current or not current.prices_synced:
        sync_prices_for_date(session, client, trade_date)
    if not current or not current.adj_synced:
        sync_adj_factor_for_date(session, client, trade_date)


def run_sync() -> None:
    session_factory = get_session_factory()
    client = TushareClient()
    with session_factory() as session:
        bootstrap_trade_calendar(session, client)
        maybe_refresh_stock_basic(session, client)
        try:
            bootstrap_index_members(session, client)
            maybe_refresh_index_members(session, client)
        except Exception:
            logger.exception("Index member sync failed, continuing with daily sync")
        try:
            bootstrap_financials(session, client)
            maybe_refresh_financials(session, client)
        except Exception:
            logger.exception("Financial data sync failed, continuing with daily sync")
        try:
            bootstrap_aux(session, client)
            maybe_refresh_aux(session, client)
        except Exception:
            logger.exception("Aux data sync failed, continuing with daily sync")
        for trade_date in get_missing_dates(session):
            _sync_date(session, client, trade_date)


@dataclass
class SyncStatus:
    running: bool
    last_synced_date: str | None
    pending_dates: int
    total_synced_dates: int


def get_sync_status() -> SyncStatus:
    session_factory = get_session_factory()
    with session_factory() as session:
        pending = len(get_missing_dates(session))
        total = session.execute(
            select(func.count())
            .select_from(SyncState)
            .where(and_(SyncState.prices_synced.is_(True), SyncState.adj_synced.is_(True)))
        ).scalar_one()
        last = session.execute(
            select(func.max(SyncState.trade_date)).where(
                and_(SyncState.prices_synced.is_(True), SyncState.adj_synced.is_(True))
            )
        ).scalar_one()
    return SyncStatus(
        running=bool(_sync_runtime["running"]),
        last_synced_date=last.strftime("%Y%m%d") if last else None,
        pending_dates=pending,
        total_synced_dates=total,
    )
