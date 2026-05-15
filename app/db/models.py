from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Numeric, String, UniqueConstraint
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


class IndexMember(Base):
    __tablename__ = "index_member"
    __table_args__ = (
        UniqueConstraint("index_code", "ts_code", "trade_date", name="uq_index_member"),
    )

    index_code: Mapped[str] = mapped_column(String, primary_key=True)
    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    weight: Mapped[float | None] = mapped_column(Numeric)


class SyncState(Base):
    __tablename__ = "sync_state"

    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    prices_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    adj_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IndexSyncState(Base):
    __tablename__ = "index_sync_state"

    index_code: Mapped[str] = mapped_column(String, primary_key=True)
    last_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinaIndicator(Base):
    __tablename__ = "fina_indicator"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", name="uq_fina_indicator"),
    )

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    eps: Mapped[float | None] = mapped_column(Numeric)
    dt_eps: Mapped[float | None] = mapped_column(Numeric)
    bps: Mapped[float | None] = mapped_column(Numeric)
    ocfps: Mapped[float | None] = mapped_column(Numeric)
    cfps: Mapped[float | None] = mapped_column(Numeric)
    total_revenue_ps: Mapped[float | None] = mapped_column(Numeric)
    revenue_ps: Mapped[float | None] = mapped_column(Numeric)
    roe: Mapped[float | None] = mapped_column(Numeric)
    roe_dt: Mapped[float | None] = mapped_column(Numeric)
    roa: Mapped[float | None] = mapped_column(Numeric)
    roic: Mapped[float | None] = mapped_column(Numeric)
    grossprofit_margin: Mapped[float | None] = mapped_column(Numeric)
    netprofit_margin: Mapped[float | None] = mapped_column(Numeric)
    profit_dedt: Mapped[float | None] = mapped_column(Numeric)
    debt_to_assets: Mapped[float | None] = mapped_column(Numeric)
    current_ratio: Mapped[float | None] = mapped_column(Numeric)
    quick_ratio: Mapped[float | None] = mapped_column(Numeric)
    cash_ratio: Mapped[float | None] = mapped_column(Numeric)
    assets_turn: Mapped[float | None] = mapped_column(Numeric)
    ar_turn: Mapped[float | None] = mapped_column(Numeric)
    ca_turn: Mapped[float | None] = mapped_column(Numeric)
    fa_turn: Mapped[float | None] = mapped_column(Numeric)
    turn_days: Mapped[float | None] = mapped_column(Numeric)
    op_income: Mapped[float | None] = mapped_column(Numeric)
    ebit: Mapped[float | None] = mapped_column(Numeric)
    ebitda: Mapped[float | None] = mapped_column(Numeric)
    fcff: Mapped[float | None] = mapped_column(Numeric)
    fcfe: Mapped[float | None] = mapped_column(Numeric)
    interestdebt: Mapped[float | None] = mapped_column(Numeric)
    netdebt: Mapped[float | None] = mapped_column(Numeric)
    invest_capital: Mapped[float | None] = mapped_column(Numeric)
    fixed_assets: Mapped[float | None] = mapped_column(Numeric)
    gross_margin: Mapped[float | None] = mapped_column(Numeric)
    basic_eps_yoy: Mapped[float | None] = mapped_column(Numeric)
    netprofit_yoy: Mapped[float | None] = mapped_column(Numeric)
    tr_yoy: Mapped[float | None] = mapped_column(Numeric)
    or_yoy: Mapped[float | None] = mapped_column(Numeric)
    roe_yoy: Mapped[float | None] = mapped_column(Numeric)


class IncomeStatement(Base):
    __tablename__ = "income_statement"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", name="uq_income_statement"),
    )

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    report_type: Mapped[str | None] = mapped_column(String)  # '1' = consolidated
    basic_eps: Mapped[float | None] = mapped_column(Numeric)
    diluted_eps: Mapped[float | None] = mapped_column(Numeric)
    total_revenue: Mapped[float | None] = mapped_column(Numeric)
    revenue: Mapped[float | None] = mapped_column(Numeric)
    int_income: Mapped[float | None] = mapped_column(Numeric)
    invest_income: Mapped[float | None] = mapped_column(Numeric)
    oper_cost: Mapped[float | None] = mapped_column(Numeric)
    sell_exp: Mapped[float | None] = mapped_column(Numeric)
    admin_exp: Mapped[float | None] = mapped_column(Numeric)
    fin_exp: Mapped[float | None] = mapped_column(Numeric)
    rd_exp: Mapped[float | None] = mapped_column(Numeric)
    operate_profit: Mapped[float | None] = mapped_column(Numeric)
    non_oper_income: Mapped[float | None] = mapped_column(Numeric)
    non_oper_exp: Mapped[float | None] = mapped_column(Numeric)
    total_profit: Mapped[float | None] = mapped_column(Numeric)
    income_tax: Mapped[float | None] = mapped_column(Numeric)
    n_income: Mapped[float | None] = mapped_column(Numeric)
    n_income_attr_p: Mapped[float | None] = mapped_column(Numeric)
    minority_gain: Mapped[float | None] = mapped_column(Numeric)
    ebit: Mapped[float | None] = mapped_column(Numeric)
    ebitda: Mapped[float | None] = mapped_column(Numeric)


class BalanceSheet(Base):
    __tablename__ = "balance_sheet"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", name="uq_balance_sheet"),
    )

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    report_type: Mapped[str | None] = mapped_column(String)
    total_assets: Mapped[float | None] = mapped_column(Numeric)
    total_liab: Mapped[float | None] = mapped_column(Numeric)
    total_hldr_eqy_exc_min_int: Mapped[float | None] = mapped_column(Numeric)
    total_hldr_eqy_inc_min_int: Mapped[float | None] = mapped_column(Numeric)
    total_cur_assets: Mapped[float | None] = mapped_column(Numeric)
    total_cur_liab: Mapped[float | None] = mapped_column(Numeric)
    money_cap: Mapped[float | None] = mapped_column(Numeric)
    accounts_receiv: Mapped[float | None] = mapped_column(Numeric)
    notes_receiv: Mapped[float | None] = mapped_column(Numeric)
    inventories: Mapped[float | None] = mapped_column(Numeric)
    fix_assets: Mapped[float | None] = mapped_column(Numeric)
    intan_assets: Mapped[float | None] = mapped_column(Numeric)
    goodwill: Mapped[float | None] = mapped_column(Numeric)
    lt_borr: Mapped[float | None] = mapped_column(Numeric)
    st_borr: Mapped[float | None] = mapped_column(Numeric)
    notes_payable: Mapped[float | None] = mapped_column(Numeric)
    acct_payable: Mapped[float | None] = mapped_column(Numeric)
    total_share: Mapped[float | None] = mapped_column(Numeric)
    cap_rese: Mapped[float | None] = mapped_column(Numeric)
    surplus_rese: Mapped[float | None] = mapped_column(Numeric)
    undistr_porfit: Mapped[float | None] = mapped_column(Numeric)
    minority_int: Mapped[float | None] = mapped_column(Numeric)


class CashFlow(Base):
    __tablename__ = "cash_flow"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", name="uq_cash_flow"),
    )

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    report_type: Mapped[str | None] = mapped_column(String)
    n_cashflow_act: Mapped[float | None] = mapped_column(Numeric)
    n_cashflow_inv_act: Mapped[float | None] = mapped_column(Numeric)
    n_cashflow_fin_act: Mapped[float | None] = mapped_column(Numeric)
    n_cash_flows_fnc_act: Mapped[float | None] = mapped_column(Numeric)
    c_cash_equ_end_period: Mapped[float | None] = mapped_column(Numeric)
    c_cash_equ_beg_period: Mapped[float | None] = mapped_column(Numeric)
    free_cashflow: Mapped[float | None] = mapped_column(Numeric)
    net_profit: Mapped[float | None] = mapped_column(Numeric)


class Dividend(Base):
    __tablename__ = "dividend"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", "div_proc", name="uq_dividend"),
    )

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    div_proc: Mapped[str] = mapped_column(String, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    stk_div: Mapped[float | None] = mapped_column(Numeric)
    stk_bo_rate: Mapped[float | None] = mapped_column(Numeric)
    stk_co_rate: Mapped[float | None] = mapped_column(Numeric)
    cash_div: Mapped[float | None] = mapped_column(Numeric)
    cash_div_tax: Mapped[float | None] = mapped_column(Numeric)
    record_date: Mapped[date | None] = mapped_column(Date)
    ex_date: Mapped[date | None] = mapped_column(Date)
    pay_date: Mapped[date | None] = mapped_column(Date)
    div_listdate: Mapped[date | None] = mapped_column(Date)
    imp_ann_date: Mapped[date | None] = mapped_column(Date)


class SuspendD(Base):
    __tablename__ = "suspend_d"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    suspend_timing: Mapped[str | None] = mapped_column(String)
    suspend_type: Mapped[str] = mapped_column(String, nullable=False)


class Forecast(Base):
    __tablename__ = "forecast"
    __table_args__ = (
        UniqueConstraint("ts_code", "end_date", name="uq_forecast"),
    )

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    type: Mapped[str | None] = mapped_column(String)
    p_change_min: Mapped[float | None] = mapped_column(Numeric)
    p_change_max: Mapped[float | None] = mapped_column(Numeric)
    net_profit_min: Mapped[float | None] = mapped_column(Numeric)
    net_profit_max: Mapped[float | None] = mapped_column(Numeric)
    last_parent_net: Mapped[float | None] = mapped_column(Numeric)
    first_ann_date: Mapped[date | None] = mapped_column(Date)
    summary: Mapped[str | None] = mapped_column(String)
    change_reason: Mapped[str | None] = mapped_column(String)


class StkHolderNumber(Base):
    __tablename__ = "stk_holdernumber"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ann_date: Mapped[date | None] = mapped_column(Date)
    holder_num: Mapped[int | None] = mapped_column(Numeric)


class AuxSyncState(Base):
    __tablename__ = "aux_sync_state"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FinaSyncState(Base):
    __tablename__ = "fina_sync_state"

    ts_code: Mapped[str] = mapped_column(String, primary_key=True)
    last_end_date: Mapped[date | None] = mapped_column(Date)
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
