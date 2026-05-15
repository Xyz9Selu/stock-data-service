from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import BalanceSheet, CashFlow, FinaIndicator, FinaSyncState, IncomeStatement, StockBasic
from app.sync.tushare_client import TushareClient

logger = logging.getLogger(__name__)

_FINA_REFRESH_DAYS = 7

_FINA_FIELDS = (
    "ts_code,ann_date,end_date,eps,dt_eps,bps,ocfps,cfps,total_revenue_ps,revenue_ps,"
    "roe,roe_dt,roa,roic,grossprofit_margin,netprofit_margin,profit_dedt,"
    "debt_to_assets,current_ratio,quick_ratio,cash_ratio,assets_turn,ar_turn,ca_turn,fa_turn,"
    "turn_days,op_income,ebit,ebitda,fcff,fcfe,interestdebt,netdebt,invest_capital,"
    "fixed_assets,gross_margin,basic_eps_yoy,netprofit_yoy,tr_yoy,or_yoy,roe_yoy"
)

_INCOME_FIELDS = (
    "ts_code,ann_date,end_date,report_type,basic_eps,diluted_eps,total_revenue,revenue,"
    "int_income,invest_income,oper_cost,sell_exp,admin_exp,fin_exp,rd_exp,"
    "operate_profit,non_oper_income,non_oper_exp,total_profit,income_tax,"
    "n_income,n_income_attr_p,minority_gain,ebit,ebitda"
)

_BALANCE_FIELDS = (
    "ts_code,ann_date,end_date,report_type,total_assets,total_liab,"
    "total_hldr_eqy_exc_min_int,total_hldr_eqy_inc_min_int,total_cur_assets,total_cur_liab,"
    "money_cap,accounts_receiv,notes_receiv,inventories,"
    "fix_assets,intan_assets,goodwill,lt_borr,st_borr,"
    "notes_payable,acct_payable,total_share,cap_rese,surplus_rese,undistr_porfit,minority_int"
)

_CASHFLOW_FIELDS = (
    "ts_code,ann_date,end_date,report_type,n_cashflow_act,n_cashflow_inv_act,"
    "n_cashflow_fin_act,n_cash_flows_fnc_act,c_cash_equ_end_period,c_cash_equ_beg_period,"
    "free_cashflow,net_profit"
)


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


def _upsert_df(
    session: Session,
    model: type,
    df,
    field_map: dict[str, str] | None = None,
) -> int:
    records: list[dict[str, object | None]] = []
    for _, row in df.iterrows():
        record: dict[str, object | None] = {}
        for col in df.columns:
            target = (field_map or {}).get(col, col)
            if col == "ts_code":
                record[target] = str(row[col])
            elif col in ("ann_date", "end_date"):
                record[target] = _parse_date(row[col])
            elif col.endswith("_date"):
                record[target] = _parse_date(row[col])
            elif col == "report_type":
                record[target] = str(row[col]) if row[col] is not None else None
            else:
                val = row[col]
                record[target] = float(val) if val is not None else None
        records.append(record)
    count = 0
    for rec in records:
        try:
            stmt = pg_insert(model).values(**rec)
            stmt = stmt.on_conflict_do_update(
                index_elements=[col.name for col in model.__table__.primary_key.columns],
                set_={k: stmt.excluded[k] for k in rec if k not in {"ts_code", "end_date"}},
            )
            session.execute(stmt)
            count += 1
        except Exception:
            continue
    session.commit()
    return count


def _sync_stock(session: Session, client: TushareClient, ts_code: str) -> int:
    total = 0
    for fields, model in [
        (_FINA_FIELDS, FinaIndicator),
        (_INCOME_FIELDS, IncomeStatement),
        (_BALANCE_FIELDS, BalanceSheet),
        (_CASHFLOW_FIELDS, CashFlow),
    ]:
        api_name = {
            FinaIndicator: "fina_indicator",
            IncomeStatement: "income",
            BalanceSheet: "balancesheet",
            CashFlow: "cashflow",
        }[model]
        try:
            method = getattr(client._api, api_name)
            df = method(ts_code=ts_code, fields=fields)
            if df is not None and len(df) > 0:
                total += _upsert_df(session, model, df)
        except Exception:
            logger.debug("Failed to fetch %s for %s", api_name, ts_code)
    return total


def bootstrap_financials(
    session: Session, client: TushareClient
) -> dict[str, int]:
    results: dict[str, int] = {}
    stocks = session.execute(
        select(StockBasic.ts_code).where(
            StockBasic.list_status.in_(["L", "D"])
        )
    ).scalars().all()
    now = datetime.now(timezone.utc)
    for idx, ts_code in enumerate(stocks):
        existing = session.execute(
            select(func.count()).select_from(FinaSyncState).where(
                FinaSyncState.ts_code == ts_code
            )
        ).scalar_one()
        if existing > 0:
            continue
        count = _sync_stock(session, client, ts_code)
        if count > 0:
            max_end = session.execute(
                select(func.max(FinaIndicator.end_date)).where(
                    FinaIndicator.ts_code == ts_code
                )
            ).scalar_one()
            session.execute(
                pg_insert(FinaSyncState)
                .values(ts_code=ts_code, last_end_date=max_end, refreshed_at=now)
                .on_conflict_do_nothing(index_elements=[FinaSyncState.ts_code])
            )
            session.commit()
        results[ts_code] = count
        if (idx + 1) % 500 == 0:
            logger.info("Fina bootstrap progress: %d/%d", idx + 1, len(stocks))
    return results


def maybe_refresh_financials(
    session: Session, client: TushareClient
) -> dict[str, int]:
    results: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    stocks = session.execute(
        select(StockBasic.ts_code).where(StockBasic.list_status == "L")
    ).scalars().all()
    for idx, ts_code in enumerate(stocks):
        state = session.get(FinaSyncState, ts_code)
        if state is not None and state.refreshed_at is not None:
            delta = now - state.refreshed_at
            if delta.days <= _FINA_REFRESH_DAYS:
                continue
        last_end = state.last_end_date if state else None
        count = _sync_stock(session, client, ts_code)
        if count > 0:
            max_end = session.execute(
                select(func.max(FinaIndicator.end_date)).where(
                    FinaIndicator.ts_code == ts_code
                )
            ).scalar_one()
            session.execute(
                pg_insert(FinaSyncState)
                .values(ts_code=ts_code, last_end_date=max_end, refreshed_at=now)
                .on_conflict_do_update(
                    index_elements=[FinaSyncState.ts_code],
                    set_={"last_end_date": max_end, "refreshed_at": now},
                )
            )
            session.commit()
        results[ts_code] = count
    return results
