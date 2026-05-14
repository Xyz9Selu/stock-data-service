## 1. Project Setup

- [x] 1.1 Add dependencies to `pyproject.toml`: `tushare`, `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `python-dotenv`
- [x] 1.2 Create project structure: `app/` with `db/`, `sync/`, `api/` sub-packages and `__init__.py` files
- [x] 1.3 Create `app/config.py` to load `TUSHARE_TOKEN` and `POSTGRES_*` vars from `.env`

## 2. Database Layer

- [x] 2.1 Create `app/db/models.py` defining SQLAlchemy ORM models for `trade_calendar`, `stock_basic`, `stock_daily`, `stock_adj_factor`, `sync_state`
- [x] 2.2 Create `app/db/migrations.py` (or Alembic setup) to create all tables on startup
- [x] 2.3 Create `app/db/session.py` with SQLAlchemy engine and session factory driven by config

## 3. Tushare Client

- [x] 3.1 Create `app/sync/tushare_client.py` wrapping `tushare.pro_api()` initialization and exposing typed fetch methods: `fetch_trade_calendar()`, `fetch_stock_basic(list_status)`, `fetch_daily(trade_date)`, `fetch_daily_basic(trade_date)`, `fetch_adj_factor(trade_date)`
- [x] 3.2 Implement rate-limiting in client: 200ms sleep between calls
- [x] 3.3 Implement retry logic: up to 3 attempts with exponential backoff (1s, 2s, 4s) on Tushare exceptions

## 4. Bootstrap Logic

- [x] 4.1 Create `app/sync/bootstrap.py` with `bootstrap_trade_calendar()`: fetch full calendar (2005-01-01 to today) if `trade_calendar` is empty
- [x] 4.2 Implement `bootstrap_stock_basic()`: fetch list_status L, D, P; upsert all into `stock_basic` with `updated_at=now()`
- [x] 4.3 Implement `maybe_refresh_stock_basic()`: check `MAX(updated_at)` in `stock_basic`; call `bootstrap_stock_basic()` if older than 7 days

## 5. Sync Engine

- [x] 5.1 Create `app/sync/engine.py` with `get_missing_dates()`: query `trade_calendar` for all open dates before today (CST) that are not fully complete in `sync_state`; return ordered oldest-first (same query serves both first-run backfill and daily catch-up)
- [x] 5.2 Implement `sync_prices_for_date(trade_date)`: call `fetch_daily()` + `fetch_daily_basic()`, merge on `ts_code`, upsert into `stock_daily`, set `sync_state.prices_synced=TRUE`
- [x] 5.3 Implement `sync_adj_factor_for_date(trade_date)`: call `fetch_adj_factor()`, upsert into `stock_adj_factor`, set `sync_state.adj_synced=TRUE`
- [x] 5.4 Implement `run_sync()`: orchestrate bootstrap → gap detection → per-date loop (oldest first); handle partial state (skip already-synced fields per date)
- [x] 5.5 Implement concurrency guard: check/set a `sync_running` flag (DB row or in-memory lock) so only one sync job runs at a time

## 6. HTTP API

- [x] 6.1 Create `app/api/router.py` with FastAPI router; mount at app root
- [x] 6.2 Implement `POST /sync/trigger`: check lock before dispatch; if running return 409; start `run_sync()` as background task; return `{ job_id, status: "started" }` with 202 (no date param)
- [x] 6.3 Implement `GET /sync/status`: return `{ running, last_synced_date, pending_dates, total_synced_dates }`
- [x] 6.4 Update `main.py` to create FastAPI app, run DB migrations on startup, and mount router

## 7. Verification

- [x] 7.1 Run DB migrations and verify all tables are created correctly
- [x] 7.2 Test bootstrap: confirm `trade_calendar` and `stock_basic` are populated on first run
- [x] 7.3 Test `POST /sync/trigger` with no body: confirm job starts and status reflects running
- [x] 7.4 Test `GET /sync/status` during and after sync run
- [x] 7.5 Spot-check `stock_daily` rows: verify `open/high/low/close` are unadjusted and `adj_factor` rows exist for same dates
- [x] 7.6 Verify concurrent trigger returns 409
- [x] 7.7 Verify mid-day trigger does not sync today's date
