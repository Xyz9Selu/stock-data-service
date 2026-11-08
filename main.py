from __future__ import annotations

import argparse
import sys

import uvicorn

from app.api import create_app
from app.config import Settings
from app.db.migrations import run_migrations
from app.sync.engine import run_sync


def run_server() -> None:
    settings = Settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )


def run_adj_audit(dates: str, dry_run: bool) -> None:
    from datetime import datetime

    from app.db.session import get_session_factory
    from app.sync.engine import find_adj_revisions, repair_adj_revisions
    from app.sync.tushare_client import TushareClient

    days = [datetime.strptime(d.strip(), "%Y%m%d").date() for d in dates.split(",") if d.strip()]
    if not days:
        raise SystemExit("adj-audit needs --dates YYYYMMDD[,YYYYMMDD...]")
    client = TushareClient()
    with get_session_factory()() as session:
        if dry_run:
            for d in days:
                print(d, find_adj_revisions(session, client, d))
        else:
            print(repair_adj_revisions(session, client, days))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="stock-data-service local runner")
    parser.add_argument(
        "command",
        choices=["migrate", "serve", "start", "sync", "adj-audit"],
        nargs="?",
        default="start",
        help="migrate: run DB migration only, serve: run API only, start: migrate then serve, "
             "sync: run full data sync once and exit, "
             "adj-audit: compare stored adj_factor on --dates with Tushare and re-pull revised stocks",
    )
    parser.add_argument("--dates", default="", help="adj-audit: comma-separated YYYYMMDD")
    parser.add_argument("--dry-run", action="store_true", help="adj-audit: report only")
    return parser.parse_args()


app = create_app()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "migrate":
            run_migrations()
            print("Migrations completed.")
            return 0
        if args.command == "serve":
            run_server()
            return 0
        if args.command == "adj-audit":
            run_adj_audit(args.dates, args.dry_run)
            return 0
        if args.command == "sync":
            run_migrations()
            print("Migrations completed. Starting data sync...")
            run_sync()
            print("Sync completed.")
            return 0

        run_migrations()
        print("Migrations completed. Starting API server.")
        run_server()
        return 0
    except Exception as exc:  # pylint: disable=broad-exception-caught  # pragma: no cover
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
