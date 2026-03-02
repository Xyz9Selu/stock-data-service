## Context

This is a greenfield Python service (`stock-data-service`) backed by PostgreSQL. Currently `main.py` is a placeholder stub. The service needs to sync Chinese A-share daily trade data from Tushare into PostgreSQL, covering all stocks from 2005-01-01 to the current date, with incremental daily updates thereafter.

The Tushare account has **2000 points**, allowing rate-limited but unrestricted access to `daily`, `daily_basic`, and `adj_factor` APIs. The token is stored in `.env` as `TUSHARE_TOKEN`.

## Goals / Non-Goals

**Goals:**
- Fetch and store unadjusted (original) daily OHLCV + fundamental metrics for all A-share stocks
- Store cumulative adjust factors (one row per stock per trading date) for downstream 复权 computation
- Support incremental gap-fill: detect missing trading dates and sync oldest-first
- Trigger sync via HTTP API or daily scheduler (post-market, CST)
- Maintain reference data: trade calendar and stock catalogue (all statuses: L/D/P), weekly refresh

**Non-Goals:**
- Serving/querying stock data via API (out of scope for now)
- Pre-computing adjusted prices (consumers use raw price × adj_factor)
- Real-time (intraday) data
- Data from exchanges other than SSE/SZSE (A-shares only)

## Decisions

### 1. Unified gap-fill sync (no separate init vs. daily sync)

**Decision**: There is a single sync operation. When triggered (via API or scheduler), the engine queries for all open trading dates before today (CST) that are not yet fully complete in `sync_state`, orders them oldest-first, and processes each in sequence. This is identical whether it is the very first run (full backfill from 2005-01-01) or a routine daily catch-up (one date).

**Rationale**: Splitting "initial backfill" from "daily incremental" adds unnecessary complexity — separate code paths, separate trigger parameters, separate state. A single gap-fill query (`SELECT cal_date FROM trade_calendar WHERE is_open=TRUE AND cal_date < today AND cal_date NOT IN (SELECT trade_date FROM sync_state WHERE prices_synced AND adj_synced)`) handles both cases identically. The trigger accepts no parameters; scope is always "everything not yet done up to yesterday".

**Rationale for date-centric (vs. stock-centric)**: Tushare's `daily(trade_date=...)` and `adj_factor(trade_date=...)` return all stocks in one response, making one call per date natural and efficient. Stock-centric sync would require tracking state per (stock, date), making gap detection complex.

### 2. Three API calls per trading date

**Decision**: Per trading date: `pro.daily()` + `pro.daily_basic()` + `pro.adj_factor()`.

**Rationale**: `daily` provides OHLCV; `daily_basic` provides market cap, turnover, PE/PB/PS ratios and other fundamental metrics not available in `daily`. Results are merged by `ts_code` into a single `stock_daily` row. `adj_factor` is kept separate in `stock_adj_factor` to preserve schema clarity.

**Alternative considered**: Fetching `daily_basic` per stock rather than per date — rejected because it would multiply API calls by ~5000×.

### 3. Rate limiting: 200ms between calls

**Decision**: Sleep 200ms between each Tushare API call during backfill (~300 calls/min).

**Rationale**: Tushare's 2000-point tier supports ~500 calls/min for these APIs. 200ms provides a 40% safety margin to avoid hitting burst limits. For the daily incremental run (3 calls/day), rate limiting has negligible impact.

### 4. Separate `sync_state` flags per data type

**Decision**: `sync_state(trade_date, prices_synced, adj_synced, completed_at)`.

**Rationale**: `daily`+`daily_basic` could succeed while `adj_factor` fails (or vice versa). Having independent flags allows retry of just the failed fetch without re-fetching the other, avoiding wasted API calls and duplicate data.

### 5. Mid-day trigger safety

**Decision**: When sync is triggered, only process dates strictly before today (CST time).

**Rationale**: Market closes at 15:00 CST. A trigger at 14:00 would fetch an incomplete trading day. Tushare may return partial data. Exclusion of today's date is the simplest safe policy; the daily scheduler is set to fire at 18:00 CST, after settlement.

### 6. `stock_basic` weekly refresh, all statuses

**Decision**: Refresh `stock_basic` weekly via UPSERT covering `list_status` values L (listed), D (delisted), P (paused).

**Rationale**: New stocks list regularly; without refresh, `stock_daily` rows for new stocks have no corresponding `stock_basic` entry. Delisted stocks must be included because historical data (pre-delisting) is valid and used in backtesting. Weekly is frequent enough to catch new listings without excessive API overhead.

### 7. Async HTTP API (fire-and-forget)

**Decision**: `POST /sync/trigger` dispatches `run_sync()` as a FastAPI `BackgroundTask` and returns immediately with `{ job_id, status: "started" }` (HTTP 202). An `asyncio.Lock` guards against concurrent runs. Progress is polled via `GET /sync/status`.

**Implementation shape**:
```python
_sync_lock = asyncio.Lock()
_sync_state = {"running": False, "job_id": None}

@router.post("/sync/trigger")
async def trigger_sync(background_tasks: BackgroundTasks, ...):
    if _sync_lock.locked():                    # ← check BEFORE acquiring
        raise HTTPException(409, "sync_already_running")
    job_id = str(uuid4())
    background_tasks.add_task(_run_sync_task, job_id, ...)
    return {"job_id": job_id, "status": "started"}

async def _run_sync_task(job_id, ...):
    async with _sync_lock:                     # ← acquire for duration of job
        _sync_state["running"] = True
        _sync_state["job_id"] = job_id
        try:
            await run_sync(...)
        finally:
            _sync_state["running"] = False
```

**Rationale**: A full backfill or even a single date's sync (3 Tushare calls + DB upserts) takes 10–30 seconds. A synchronous response would hold the connection open and risk client timeout. `asyncio.Lock` is the correct primitive because sync runs within the same async event loop. Checking `_sync_lock.locked()` before acquiring gives an immediate 409 without blocking.

**Alternative considered**: A DB-level `sync_running` flag — rejected in favour of `asyncio.Lock` for simplicity, since the service is single-process. If multi-process deployment is needed in future, the DB flag approach should be revisited.

## Database Schema

```sql
-- Reference: valid trading dates
CREATE TABLE trade_calendar (
  cal_date  DATE PRIMARY KEY,
  is_open   BOOLEAN NOT NULL
);

-- Reference: stock catalogue (all statuses)
CREATE TABLE stock_basic (
  ts_code      TEXT PRIMARY KEY,   -- e.g. '000001.SZ'
  symbol       TEXT,
  name         TEXT,
  area         TEXT,
  industry     TEXT,
  market       TEXT,
  exchange     TEXT,
  list_status  CHAR(1),            -- 'L' / 'D' / 'P'
  list_date    DATE,
  delist_date  DATE,
  is_hs        CHAR(1),
  updated_at   TIMESTAMPTZ
);

-- Daily prices (unadjusted) + fundamentals
CREATE TABLE stock_daily (
  ts_code         TEXT,
  trade_date      DATE,
  -- from pro.daily()
  open            NUMERIC,
  high            NUMERIC,
  low             NUMERIC,
  close           NUMERIC,
  pre_close       NUMERIC,
  change          NUMERIC,
  pct_chg         NUMERIC,
  vol             NUMERIC,
  amount          NUMERIC,
  -- from pro.daily_basic()
  turnover_rate   NUMERIC,
  turnover_rate_f NUMERIC,
  volume_ratio    NUMERIC,
  pe              NUMERIC,
  pe_ttm          NUMERIC,
  pb              NUMERIC,
  ps              NUMERIC,
  ps_ttm          NUMERIC,
  dv_ratio        NUMERIC,
  dv_ttm          NUMERIC,
  total_share     NUMERIC,
  float_share     NUMERIC,
  free_share      NUMERIC,
  total_mv        NUMERIC,
  circ_mv         NUMERIC,
  PRIMARY KEY (ts_code, trade_date)
);

-- Adjust factors: cumulative hfq factor per stock per trading date
CREATE TABLE stock_adj_factor (
  ts_code     TEXT,
  trade_date  DATE,
  adj_factor  NUMERIC NOT NULL,
  PRIMARY KEY (ts_code, trade_date)
);

-- Sync progress: per trading date
CREATE TABLE sync_state (
  trade_date      DATE PRIMARY KEY,
  prices_synced   BOOLEAN DEFAULT FALSE,
  adj_synced      BOOLEAN DEFAULT FALSE,
  completed_at    TIMESTAMPTZ
);
```

## Risks / Trade-offs

- **Tushare API instability** → Mitigation: retry logic with exponential backoff (3 attempts); failed dates marked in `sync_state` for automatic retry next run
- **Backfill duration (~50 min)** → Mitigation: backfill runs unattended; API trigger returns immediately; progress visible via `/sync/status`
- **`daily_basic` sparse data for early dates (pre-2010)** → Mitigation: allow NULL columns in `stock_daily`; upsert only available fields
- **Concurrent trigger calls** → Mitigation: advisory lock or DB-level flag (`sync_running`) to prevent parallel sync runs
- **New stocks missing from `stock_basic`** → Mitigation: weekly refresh ensures new listings appear within 7 days; `stock_daily` FK is nullable to allow orphan rows

## Migration Plan

1. Run DB migrations to create all tables
2. Bootstrap `trade_calendar` (one-time: Tushare `trade_cal` API, full range)
3. Bootstrap `stock_basic` (one-time: all three `list_status` values)
4. Trigger backfill via `POST /sync/trigger` — sync engine processes all missing dates from 2005-01-01
5. Daily scheduler maintains freshness thereafter

Rollback: drop tables (no existing data at risk — greenfield service).

## Open Questions

- *(none — all decisions made during explore phase)*
