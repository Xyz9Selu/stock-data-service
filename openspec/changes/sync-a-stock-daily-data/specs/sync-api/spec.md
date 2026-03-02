## ADDED Requirements

### Requirement: Trigger sync via HTTP POST
The system SHALL expose a `POST /sync/trigger` endpoint that accepts no parameters and starts an asynchronous sync job. The job SHALL sync all trading dates from the latest fully-synced date up to the latest available trade date before today (CST). The endpoint SHALL return immediately with a job identifier and status without waiting for sync completion.

#### Scenario: Trigger incremental sync
- **WHEN** a client sends `POST /sync/trigger`
- **THEN** the system SHALL start an async sync job covering all unsynced trading dates from the day after the latest completed date up to but not including today
- **THEN** the response SHALL be `{ "job_id": "<uuid>", "status": "started" }` with HTTP 202

#### Scenario: Nothing to sync
- **WHEN** `POST /sync/trigger` is called and all trading dates up to yesterday are already fully synced
- **THEN** the system SHALL start a background task that exits immediately after detecting no gaps
- **THEN** the response SHALL still be `{ "job_id": "<uuid>", "status": "started" }` with HTTP 202

#### Scenario: Trigger rejected — sync already running
- **WHEN** a sync job is already in progress and a new `POST /sync/trigger` is received
- **THEN** the system SHALL return HTTP 409 with `{ "error": "sync_already_running", "message": "A sync job is already in progress" }`

---

### Requirement: Sync task runs asynchronously as a background process
The system SHALL dispatch the sync job as an async background task upon receiving `POST /sync/trigger`, so that the HTTP response is returned to the client before any sync work begins. The sync task SHALL acquire an async lock for its entire duration. The system SHALL check whether the lock is already held **before** dispatching the background task and reject the request immediately with HTTP 409 if so, without queuing or blocking.

#### Scenario: Response returned before sync starts
- **WHEN** `POST /sync/trigger` is accepted
- **THEN** the HTTP response (202) SHALL be sent to the client before `run_sync()` begins executing
- **THEN** the sync job SHALL run in the background without blocking new HTTP requests

#### Scenario: Running check is pre-dispatch (not queued)
- **WHEN** a sync job is running and a second `POST /sync/trigger` arrives
- **THEN** the system SHALL detect the running state before dispatching any background task
- **THEN** the system SHALL return HTTP 409 immediately — it SHALL NOT queue the second job to run after the first completes

#### Scenario: Lock released after sync completes or errors
- **WHEN** a sync job finishes (successfully or with error)
- **THEN** the async lock SHALL be released
- **THEN** subsequent `POST /sync/trigger` calls SHALL be accepted normally

### Requirement: Query sync status via HTTP GET
The system SHALL expose a `GET /sync/status` endpoint that returns the current sync state including the most recently completed date, the count of pending dates, and whether a sync is currently running.

#### Scenario: Status while idle and up-to-date
- **WHEN** no sync is running and all trading dates are synced
- **THEN** `GET /sync/status` SHALL return HTTP 200 with:
  ```json
  {
    "running": false,
    "last_synced_date": "20250301",
    "pending_dates": 0,
    "total_synced_dates": 5000
  }
  ```

#### Scenario: Status while sync is running
- **WHEN** a sync job is in progress
- **THEN** `GET /sync/status` SHALL return HTTP 200 with `"running": true` and current `pending_dates` count

#### Scenario: Status after partial failure
- **WHEN** some dates failed (prices_synced or adj_synced is FALSE)
- **THEN** the response SHALL include those dates in `pending_dates` count
