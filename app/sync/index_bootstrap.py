from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import IndexMember, IndexSyncState, StockBasic
from app.sync.index_client import TRACKED_INDICES, IndexDataClient
from app.sync.tushare_client import TushareClient

logger = logging.getLogger(__name__)

_INDEX_REFRESH_DAYS = 30


def _to_ts_index_code(ak_code: str) -> str:
    if ak_code.startswith("399"):
        return f"{ak_code}.SZ"
    return f"{ak_code}.SH"


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


def _sync_from_tushare(session: Session, index_code: str, ts_client: TushareClient, launch_year: int = 2005) -> int:
    ts_code = _to_ts_index_code(index_code)
    total = 0
    now = datetime.now(timezone.utc)
    start_year = max(2016, launch_year)

    for year in range(start_year, now.year + 1):
        try:
            df = ts_client._api.index_weight(
                index_code=ts_code,
                start_date=f"{year}0101",
                end_date=f"{year}1231",
            )
        except Exception:
            continue
        if df is None or len(df) == 0:
            continue

        df["trade_date"] = df["trade_date"].astype(str)
        for month_str in df["trade_date"].unique():
            month_df = df[df["trade_date"] == month_str]
            month_dt = _parse_date(month_str)
            if month_dt is None:
                continue
            for _, row in month_df.iterrows():
                try:
                    stmt = pg_insert(IndexMember).values(
                        index_code=ts_code,
                        ts_code=str(row["con_code"]),
                        trade_date=month_dt,
                        weight=float(row["weight"]),
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[
                            IndexMember.index_code,
                            IndexMember.ts_code,
                            IndexMember.trade_date,
                        ],
                        set_={"weight": stmt.excluded.weight},
                    )
                    session.execute(stmt)
                    total += 1
                except Exception:
                    continue
            session.commit()

    session.execute(
        pg_insert(IndexSyncState)
        .values(index_code=ts_code, last_refresh_at=now)
        .on_conflict_do_update(
            index_elements=[IndexSyncState.index_code],
            set_={"last_refresh_at": now},
        )
    )
    session.commit()
    return total


def _reconstruct_from_mcap(
    session: Session, index_code: str, index_size: int, start_year: int, end_year: int
) -> int:
    ts_code = _to_ts_index_code(index_code)
    rows_inserted = 0
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            if month == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month + 1, 1)
            month_start = date(year, month, 1)
            month_end_dt = session.execute(
                text(
                    "SELECT MAX(cal_date) FROM trade_calendar "
                    "WHERE cal_date >= :start AND cal_date < :end AND is_open"
                ),
                {"start": month_start, "end": next_month},
            ).scalar_one()
            if month_end_dt is None:
                continue
            try:
                result = session.execute(
                    text(
                        """
                        INSERT INTO index_member (index_code, ts_code, trade_date, weight)
                        SELECT :idx, ts_code, :trade_dt, NULL
                        FROM stock_daily
                        WHERE trade_date = :trade_dt
                        ORDER BY circ_mv DESC NULLS LAST
                        LIMIT :size
                        ON CONFLICT (index_code, ts_code, trade_date) DO NOTHING
                        """
                    ),
                    {"idx": ts_code, "trade_dt": month_end_dt, "size": index_size},
                )
                rows_inserted += result.rowcount
            except Exception:
                continue
        session.commit()
    return rows_inserted


def _seed_current_from_akshare(session: Session, index_code: str) -> int:
    """Fetch current constituents from akshare and insert the latest month snapshot."""
    client = IndexDataClient()
    try:
        df = client.fetch_index_cons(symbol=index_code)
    except Exception:
        logger.exception("akshare fetch failed for %s", index_code)
        return 0

    code_map = {
        row.symbol: row.ts_code
        for row in session.execute(select(StockBasic.symbol, StockBasic.ts_code)).all()
        if row.symbol
    }
    ts_code = _to_ts_index_code(index_code)
    trade_date = date.today().replace(day=1)
    inserted = 0
    for _, row in df.iterrows():
        short = str(row["品种代码"])
        mapped = code_map.get(short)
        if mapped is None:
            continue
        try:
            stmt = pg_insert(IndexMember).values(
                index_code=ts_code,
                ts_code=mapped,
                trade_date=trade_date,
                weight=None,
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[
                    IndexMember.index_code,
                    IndexMember.ts_code,
                    IndexMember.trade_date,
                ]
            )
            session.execute(stmt)
            inserted += 1
        except Exception:
            continue
    session.commit()
    return inserted


def bootstrap_index_members(
    session: Session, ts_client: TushareClient | None = None
) -> dict[str, int]:
    results: dict[str, int] = {}

    for ak_code, _name, size, launch_year in TRACKED_INDICES:
        ts_code = _to_ts_index_code(ak_code)
        try:
            existing = session.execute(
                select(func.count()).select_from(IndexMember).where(
                    IndexMember.index_code == ts_code
                )
            ).scalar_one()
            if existing > 0:
                results[ts_code] = existing
                continue
        except Exception:
            pass

        total = 0
        if ts_client is not None:
            try:
                total += _sync_from_tushare(session, ak_code, ts_client, launch_year)
            except Exception:
                logger.exception("TuShare backfill failed for %s", ak_code)

        if launch_year < 2016:
            try:
                total += _reconstruct_from_mcap(session, ak_code, size, launch_year, 2015)
            except Exception:
                logger.exception("MCap reconstruction failed for %s", ak_code)

        try:
            total += _seed_current_from_akshare(session, ak_code)
        except Exception:
            logger.exception("akshare seed failed for %s", ak_code)

        results[ts_code] = total

    return results


def maybe_refresh_index_members(
    session: Session, ts_client: TushareClient | None = None
) -> dict[str, int]:
    results: dict[str, int] = {}
    now = datetime.now(timezone.utc)

    for ak_code, _name, _size, launch_year in TRACKED_INDICES:
        ts_code = _to_ts_index_code(ak_code)
        state = session.get(IndexSyncState, ts_code)
        if state is not None and state.last_refresh_at is not None:
            delta = now - state.last_refresh_at
            if delta.days <= _INDEX_REFRESH_DAYS:
                continue

        count = 0
        if ts_client is not None:
            try:
                count = _sync_from_tushare(session, ak_code, ts_client, launch_year)
            except Exception:
                logger.exception("Refresh failed for %s", ak_code)
        results[ts_code] = count

    return results
