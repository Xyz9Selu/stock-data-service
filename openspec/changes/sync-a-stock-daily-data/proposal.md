## Why

Chinese A-share daily trade data is needed locally to support backtesting and quantitative analysis workflows. Currently there is no automated mechanism to fetch, store, or incrementally update this data. This change establishes a Tushare-backed sync service with PostgreSQL storage, enabling reliable, incremental daily data collection triggered on-demand via HTTP API.

## What Changes

- Introduce a **stock daily sync engine** that fetches all A-share OHLCV + fundamental metrics + adjust factors for each trading date from Tushare, storing unadjusted (original) prices alongside their cumulative adjust factors
- Introduce a **sync HTTP API** to trigger sync on-demand (`POST /sync/trigger`) and query sync status (`GET /sync/status`)
- Bootstrap supporting reference data: trade calendar (`trade_calendar`) and stock catalogue (`stock_basic`), including active, delisted, and paused stocks; `stock_basic` refreshed weekly
- Sync strategy is **unified gap-fill**: iterate all unsynced trading dates oldest-first, identically for first-run backfill and daily catch-up

## Capabilities

### New Capabilities

- `stock-daily-sync`: Core sync engine — gap detection, date-by-date fetch loop, upsert logic for prices, fundamentals, and adjust factors into PostgreSQL
- `sync-api`: HTTP API to trigger sync (`POST /sync/trigger`) and query status (`GET /sync/status`)

### Modified Capabilities

*(none — this is a greenfield service)*

## Impact

- **New dependencies**: `tushare`, `fastapi`, `uvicorn`, `psycopg2-binary`, `sqlalchemy`, `python-dotenv`
- **New DB tables**: `trade_calendar`, `stock_basic`, `stock_daily`, `stock_adj_factor`, `sync_state`
- **Config**: `TUSHARE_TOKEN` already present in `.env`; `POSTGRES_*` vars already present
- **Tushare API calls**: 3 calls per trading date (`daily`, `daily_basic`, `adj_factor`); ~15,000 calls for full 2005–present backfill; rate-limited to 200ms between calls (safe for 2000-point account)
