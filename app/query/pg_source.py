"""Serve daily / daily_basic / adj_factor from the synced PostgreSQL tables.

The nightly sync already stores these three APIs in full (stock_daily holds
daily + daily_basic columns, stock_adj_factor the factors), so a request the
tables fully cover is answered locally instead of calling Tushare and writing
a cache file. Anything else falls back to Tushare: unknown params or fields,
no ts_code/trade_date, or a range reaching past the last synced trade date.
"""
from __future__ import annotations

import time
from datetime import date, datetime
from zoneinfo import ZoneInfo
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.config import Settings
from app.db.session import get_engine

DAILY_COLS = ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]
BASIC_COLS = [
    "turnover_rate", "turnover_rate_f", "volume_ratio", "pe", "pe_ttm", "pb", "ps", "ps_ttm",
    "dv_ratio", "dv_ttm", "total_share", "float_share", "free_share", "total_mv", "circ_mv",
]

# api -> (table, value columns in Tushare's default order, columns that must not all be null)
APIS: dict[str, tuple[str, list[str], list[str]]] = {
    "daily": ("stock_daily", DAILY_COLS, []),
    # stock_daily also keeps stocks that traded but had no daily_basic row that day
    "daily_basic": ("stock_daily", ["close", *BASIC_COLS], BASIC_COLS),
    "adj_factor": ("stock_adj_factor", ["adj_factor"], []),
}
ALLOWED_PARAMS = {"ts_code", "trade_date", "start_date", "end_date", "fields"}


def _day(s: Any) -> date:
    return datetime.strptime(str(s)[:8], "%Y%m%d").date()


class PgSource:
    def __init__(self, settings: Settings | None = None, engine: Engine | None = None) -> None:
        self.settings = settings or Settings()
        self._engine = engine

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = get_engine(self.settings)
        return self._engine

    def _plan(self, api: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if api not in APIS or set(params) - ALLOWED_PARAMS:
            return None
        table, cols, nonnull = APIS[api]
        if not params.get("ts_code") and not params.get("trade_date"):
            return None
        if params.get("trade_date"):
            if params.get("start_date") or params.get("end_date"):
                return None
            start = end = _day(params["trade_date"])
        else:
            if not params.get("start_date"):
                return None  # open-ended history: Tushare goes back before 2005
            start = _day(params["start_date"])
            end = _day(params["end_date"]) if params.get("end_date") else datetime.now(ZoneInfo("Asia/Shanghai")).date()
        if params.get("fields"):
            out = [f.strip() for f in str(params["fields"]).split(",") if f.strip()]
            if set(out) - {"ts_code", "trade_date", *cols}:
                return None
        else:
            out = ["ts_code", "trade_date", *cols]
        codes = [c.strip() for c in str(params.get("ts_code") or "").split(",") if c.strip()]
        return {"table": table, "out": out, "nonnull": nonnull, "codes": codes, "start": start, "end": end}

    def _covered(self, conn: Any, start: date, end: date) -> tuple[bool, date | None]:
        first, last = conn.execute(
            text("select min(trade_date), max(trade_date) from sync_state where prices_synced and adj_synced")
        ).one()
        if last is None or start < first:
            return False, last
        gap = conn.execute(
            text(
                "select 1 from trade_calendar c left join sync_state s on s.trade_date = c.cal_date "
                "where c.is_open and c.cal_date between :s and :e "
                "and not coalesce(s.prices_synced and s.adj_synced, false) limit 1"
            ),
            {"s": start, "e": end},
        ).first()
        return gap is None, last

    def query(self, api: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Rows in Tushare's shape, or None when the request must go to Tushare."""
        plan = self._plan(api, params)
        if plan is None:
            return None
        with self.engine.connect() as conn:
            ok, last = self._covered(conn, plan["start"], plan["end"])
            if not ok:
                return None
            select_cols = ["ts_code", "trade_date", *[c for c in plan["out"] if c not in ("ts_code", "trade_date")]]
            where = ["trade_date between :s and :e"]
            bind: dict[str, Any] = {"s": plan["start"], "e": plan["end"]}
            if plan["codes"]:
                where.append("ts_code = any(:codes)")
                bind["codes"] = plan["codes"]
            if plan["nonnull"]:
                where.append("coalesce(" + ", ".join(plan["nonnull"]) + ") is not null")
            sql = (
                f"select {', '.join(select_cols)} from {plan['table']} where {' and '.join(where)} "
                "order by trade_date desc, ts_code"
            )
            result = conn.execute(text(sql), bind)
            rows = []
            for rec in result.mappings():
                row = {}
                for k in plan["out"]:
                    v = rec[k]
                    if k == "trade_date":
                        v = v.strftime("%Y%m%d")
                    elif k != "ts_code" and v is not None:
                        v = float(v)
                    row[k] = v
                rows.append(row)
        return {
            "api": api,
            "params": params,
            "fetched_at": time.time(),
            "fetched_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "n_rows": len(rows),
            "rows": rows,
            "meta": {"source": "pg", "last_synced": last.strftime("%Y%m%d") if last else None},
            "cache_hit": True,
            "cache_path": None,
            "source": "pg",
        }
