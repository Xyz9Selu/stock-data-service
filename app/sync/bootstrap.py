from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import StockBasic, TradeCalendar
from app.sync.tushare_client import TushareClient


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%d").date()


def bootstrap_trade_calendar(session: Session, client: TushareClient) -> None:
    exists = session.execute(select(func.count()).select_from(TradeCalendar)).scalar_one()
    if exists > 0:
        return
    frame = client.fetch_trade_calendar(date(2005, 1, 1), date.today())
    records = [
        {"cal_date": _parse_date(row.cal_date), "is_open": row.is_open == 1}
        for row in frame.itertuples(index=False)
    ]
    if not records:
        return
    stmt = insert(TradeCalendar).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=[TradeCalendar.cal_date],
        set_={"is_open": stmt.excluded.is_open},
    )
    session.execute(stmt)
    session.commit()


def bootstrap_stock_basic(session: Session, client: TushareClient) -> None:
    now = datetime.now()
    rows: list[dict[str, object | None]] = []
    for status in ("L", "D", "P"):
        frame = client.fetch_stock_basic(status)
        for rec in frame.to_dict(orient="records"):
            rows.append(
                {
                    "ts_code": rec.get("ts_code"),
                    "symbol": rec.get("symbol"),
                    "name": rec.get("name"),
                    "area": rec.get("area"),
                    "industry": rec.get("industry"),
                    "market": rec.get("market"),
                    "exchange": rec.get("exchange"),
                    "list_status": rec.get("list_status"),
                    "list_date": _parse_date(rec.get("list_date")),
                    "delist_date": _parse_date(rec.get("delist_date")),
                    "is_hs": rec.get("is_hs"),
                    "updated_at": now,
                }
            )
    if not rows:
        return
    stmt = insert(StockBasic).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[StockBasic.ts_code],
        set_={
            "symbol": stmt.excluded.symbol,
            "name": stmt.excluded.name,
            "area": stmt.excluded.area,
            "industry": stmt.excluded.industry,
            "market": stmt.excluded.market,
            "exchange": stmt.excluded.exchange,
            "list_status": stmt.excluded.list_status,
            "list_date": stmt.excluded.list_date,
            "delist_date": stmt.excluded.delist_date,
            "is_hs": stmt.excluded.is_hs,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    session.execute(stmt)
    session.commit()


def maybe_refresh_stock_basic(session: Session, client: TushareClient) -> None:
    last_update = session.execute(select(func.max(StockBasic.updated_at))).scalar_one()
    if last_update is None:
        bootstrap_stock_basic(session, client)
        return
    if datetime.now(last_update.tzinfo) - last_update > timedelta(days=7):
        bootstrap_stock_basic(session, client)
