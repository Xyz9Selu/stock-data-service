from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import AuxSyncState, Dividend, Forecast, StkHolderNumber, StockBasic, SuspendD
from app.sync.tushare_client import TushareClient

logger = logging.getLogger(__name__)

_AUX_REFRESH_DAYS = 7


def _parse_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value)
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _upsert_df(session: Session, model: type, df, extra_cols: dict[str, object] | None = None) -> int:
    count = 0
    pks = [c.name for c in model.__table__.primary_key.columns]
    date_cols = {c.name for c in model.__table__.columns if str(c.type).lower().startswith("date")}
    str_cols = ("type", "div_proc", "summary", "change_reason", "suspend_type", "suspend_timing")
    for _, row in df.iterrows():
        record: dict[str, object | None] = dict(extra_cols or {})
        for col in df.columns:
            if col == "ts_code":
                record[col] = str(row[col])
            elif col in date_cols:
                record[col] = _parse_date(row[col])
            elif col in str_cols:
                record[col] = str(row[col]) if row[col] is not None else None
            elif col in model.__table__.columns:
                val = row[col]
                record[col] = float(val) if val is not None else None
        try:
            stmt = pg_insert(model).values(**record)
            stmt = stmt.on_conflict_do_update(
                index_elements=pks,
                set_={k: stmt.excluded[k] for k in record if k not in pks},
            )
            session.execute(stmt)
            count += 1
        except Exception:
            continue
    session.commit()
    return count


def _sync_stock_aux(session: Session, client: TushareClient, ts_code: str) -> int:
    total = 0
    for api_name, model in [
        ("dividend", Dividend),
        ("suspend_d", SuspendD),
        ("forecast", Forecast),
        ("stk_holdernumber", StkHolderNumber),
    ]:
        try:
            method = getattr(client._api, api_name)
            df = method(ts_code=ts_code)
            if df is not None and len(df) > 0:
                total += _upsert_df(session, model, df)
        except Exception:
            logger.debug("Failed %s for %s", api_name, ts_code)
    return total


def bootstrap_aux(session: Session, client: TushareClient) -> dict[str, int]:
    results: dict[str, int] = {}
    stocks = session.execute(
        select(StockBasic.ts_code).where(StockBasic.list_status.in_(["L", "D"]))
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for idx, ts_code in enumerate(stocks):
        existing = session.execute(
            select(func.count()).select_from(AuxSyncState).where(AuxSyncState.ts_code == ts_code)
        ).scalar_one()
        if existing > 0:
            continue
        count = _sync_stock_aux(session, client, ts_code)
        if count > 0:
            session.execute(
                pg_insert(AuxSyncState)
                .values(ts_code=ts_code, refreshed_at=now)
                .on_conflict_do_nothing(index_elements=[AuxSyncState.ts_code])
            )
            session.commit()
        results[ts_code] = count
        if (idx + 1) % 500 == 0:
            logger.info("Aux bootstrap progress: %d/%d", idx + 1, len(stocks))
    return results


def maybe_refresh_aux(session: Session, client: TushareClient) -> dict[str, int]:
    results: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    stocks = session.execute(
        select(StockBasic.ts_code).where(StockBasic.list_status == "L")
    ).scalars().all()
    for idx, ts_code in enumerate(stocks):
        state = session.get(AuxSyncState, ts_code)
        if state is not None and state.refreshed_at is not None:
            if (now - state.refreshed_at).days <= _AUX_REFRESH_DAYS:
                continue
        count = _sync_stock_aux(session, client, ts_code)
        if count > 0:
            session.execute(
                pg_insert(AuxSyncState)
                .values(ts_code=ts_code, refreshed_at=now)
                .on_conflict_do_update(
                    index_elements=[AuxSyncState.ts_code],
                    set_={"refreshed_at": now},
                )
            )
            session.commit()
        results[ts_code] = count
    return results
