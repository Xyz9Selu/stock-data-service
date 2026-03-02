## ADDED Requirements

### Requirement: Bootstrap trade calendar
The system SHALL fetch and persist the full A-share trade calendar from Tushare (`trade_cal` API, SSE exchange) covering 2005-01-01 to at least the current date, storing each date with its `is_open` flag into the `trade_calendar` table.

#### Scenario: Trade calendar bootstrap on first run
- **WHEN** the sync engine starts and `trade_calendar` is empty
- **THEN** the system SHALL fetch all calendar records from 2005-01-01 to today and upsert them into `trade_calendar`

---

### Requirement: Bootstrap stock catalogue
The system SHALL fetch and persist A-share stock metadata for all `list_status` values (L=listed, D=delisted, P=paused) into the `stock_basic` table via Tushare `stock_basic` API, and refresh this data weekly.

#### Scenario: Initial stock catalogue population
- **WHEN** the sync engine starts and `stock_basic` is empty
- **THEN** the system SHALL fetch stocks for each of list_status L, D, and P and upsert all records

#### Scenario: Weekly stock catalogue refresh
- **WHEN** the sync engine runs and MAX(`updated_at`) in `stock_basic` is older than 7 days
- **THEN** the system SHALL re-fetch all three list_status batches and upsert into `stock_basic`

#### Scenario: Stock catalogue is fresh (within 7 days)
- **WHEN** the sync engine runs and MAX(`updated_at`) in `stock_basic` is within 7 days
- **THEN** the system SHALL skip the stock catalogue refresh

---

### Requirement: Detect unsynced trading dates
The system SHALL determine which trading dates need syncing by finding all dates in `trade_calendar` (where `is_open=TRUE`) that are strictly before today (CST) and do not have a fully-complete entry in `sync_state` (`prices_synced=TRUE AND adj_synced=TRUE`). The result SHALL be ordered oldest-first. This logic is identical whether running for the first time (full backfill from 2005-01-01) or after recent daily syncs (catching up one date).

#### Scenario: First run — full backfill
- **WHEN** `sync_state` is empty
- **THEN** the system SHALL return all open trading dates from 2005-01-01 up to but not including today, ordered ascending

#### Scenario: Incremental run — one date behind
- **WHEN** `sync_state` has all dates complete up to the day before yesterday
- **THEN** the system SHALL return only yesterday's date as the single pending date

#### Scenario: No gaps — nothing to sync
- **WHEN** all open trading dates up to yesterday are complete in `sync_state`
- **THEN** the system SHALL return an empty list and the sync job SHALL exit cleanly

#### Scenario: Mid-day trigger excludes today
- **WHEN** sync is triggered at any time on a trading day before market settlement
- **THEN** today's date SHALL NOT be included regardless of whether it appears in `trade_calendar`

---

### Requirement: Sync daily prices and fundamentals per trading date
For each missing trading date, the system SHALL fetch all stocks' OHLCV data via `pro.daily(trade_date=...)` and all stocks' fundamental metrics via `pro.daily_basic(trade_date=...)`, merge the results by `ts_code`, and upsert into `stock_daily`. On success, `prices_synced` in `sync_state` SHALL be set to TRUE for that date.

#### Scenario: Successful price sync for a date
- **WHEN** the engine processes a missing trading date
- **THEN** it SHALL call `pro.daily(trade_date=date)` and `pro.daily_basic(trade_date=date)`, merge results by `ts_code`, and upsert all rows into `stock_daily`
- **THEN** `sync_state.prices_synced` SHALL be set to TRUE for that date

#### Scenario: `daily_basic` returns no data for early dates
- **WHEN** `pro.daily_basic()` returns an empty DataFrame for a date (e.g., pre-2010)
- **THEN** the system SHALL upsert `stock_daily` rows with only the `daily` fields; fundamental columns SHALL be NULL
- **THEN** `sync_state.prices_synced` SHALL still be set to TRUE

#### Scenario: Tushare API call fails
- **WHEN** a Tushare API call raises an exception
- **THEN** the system SHALL retry up to 3 times with exponential backoff (1s, 2s, 4s)
- **THEN** if all retries fail, `sync_state.prices_synced` SHALL remain FALSE and the error SHALL be logged
- **THEN** the engine SHALL continue to the next pending date

---

### Requirement: Sync adjust factors per trading date
For each missing trading date, the system SHALL fetch cumulative adjust factors via `pro.adj_factor(trade_date=...)` and upsert all rows into `stock_adj_factor`. On success, `adj_synced` in `sync_state` SHALL be set to TRUE for that date.

#### Scenario: Successful adj factor sync for a date
- **WHEN** the engine processes adjust factors for a trading date
- **THEN** it SHALL call `pro.adj_factor(trade_date=date)` and upsert all `(ts_code, trade_date, adj_factor)` rows into `stock_adj_factor`
- **THEN** `sync_state.adj_synced` SHALL be set to TRUE for that date

#### Scenario: Partial sync state (prices done, adj not done)
- **WHEN** `sync_state.prices_synced=TRUE` but `adj_synced=FALSE` for a date
- **THEN** the engine SHALL skip the `daily`/`daily_basic` fetch and only fetch `adj_factor` for that date

---

### Requirement: Rate-limited API calls
The system SHALL enforce a minimum 200ms delay between consecutive Tushare API calls to stay within the 2000-point account's rate limits.

#### Scenario: Consecutive API calls during backfill
- **WHEN** the engine makes Tushare API calls in a loop over trading dates
- **THEN** each call SHALL be preceded by a sleep of at least 200ms

---

### Requirement: Idempotent upsert
All writes to `stock_daily` and `stock_adj_factor` SHALL use upsert semantics (`INSERT ... ON CONFLICT DO UPDATE`) so that re-running sync for an already-synced date is safe and non-destructive.

#### Scenario: Re-sync a previously completed date
- **WHEN** sync is triggered for a date already in `sync_state` as complete
- **THEN** data SHALL be upserted (not duplicated) and no error SHALL be raised
