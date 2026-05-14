# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Stock data service — fetches Chinese A-share market data from TuShare API, stores in PostgreSQL, serves via FastAPI.

## Commands

```bash
uv sync                        # Install dependencies
uv run python main.py migrate  # Run DB migrations only
uv run python main.py serve    # Start API server
uv run python main.py start    # Migrate then serve (default)
uv run python main.py -h       # CLI help
docker compose up -d db        # Start PostgreSQL dev container
```

No tests exist yet. No linter/formatter config set up.

## OpenSpec Workflow

This project uses OpenSpec (`openspec` CLI) for spec-driven development. Changes live in `openspec/changes/<name>/`.

```bash
openspec list                                   # List active changes
openspec status --change "<name>" --json        # Check status & progress
openspec instructions apply --change "<name>"   # Get apply instructions
openspec instructions <artifact> --change "<name>"  # Get artifact creation instructions
```

Changes follow a `spec-driven` schema: proposal → specs → design → tasks → implementation. View specs at `openspec/changes/<name>/specs/`.

## Architecture

```
main.py  →  app/api/  (FastAPI routes)
          →  app/db/  (SQLAlchemy models + auto-migration via create_all)
          →  app/sync/ (TuShare data sync engine)
```

### API Layer (`app/api/`)
- Factory `create_app()` builds the FastAPI app, runs migrations on startup, registers `/healthz` (DB ping) and sync routes.
- Sync routes: `POST /sync/trigger` (background job, guarded by `asyncio.Lock`, returns 409 if busy), `GET /sync/status` (running state + progress).

### DB Layer (`app/db/`)
- 6 models: `TradeCalendar`, `StockBasic`, `StockDaily` (wide table, ~30 columns), `StockAdjFactor`, `SyncState`.
- Auto-migration via `Base.metadata.create_all()` — no Alembic, no migration scripts.
- Upserts use PostgreSQL `on_conflict_do_update`.

### Sync Engine (`app/sync/`)
- `TushareClient`: wraps TuShare pro API with 0.2s throttle + exponential backoff retry (1/2/4s).
- `bootstrap.py`: seeds trade calendar (from 2005) and stock basics on first run; refreshes stock list weekly.
- `engine.py`: finds missing dates via `TradeCalendar` LEFT JOIN `SyncState`, then fetches daily prices + daily_basic + adj_factor per date.
- Sync state is per-date with `prices_synced` and `adj_synced` boolean flags.

### Config (`app/config.py`)
- `Settings` frozen dataclass, loaded from `.env` via `python-dotenv`.
- DB defaults to port 15432 (dev avoids local PG conflicts).
- No auth on any endpoint.

## Code Conventions

- `from __future__ import annotations` in every Python file
- Type hints on all signatures
- No docstrings or comments unless explaining WHY
- Conventional commits: `type: message` (feat, fix, chore, doc, refactor, test)
