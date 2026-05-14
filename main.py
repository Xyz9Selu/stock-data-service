from __future__ import annotations

import argparse
import sys

import uvicorn

from app.api import create_app
from app.config import Settings
from app.db.migrations import run_migrations


def run_server() -> None:
    settings = Settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="stock-data-service local runner")
    parser.add_argument(
        "command",
        choices=["migrate", "serve", "start"],
        nargs="?",
        default="start",
        help="migrate: run DB migration only, serve: run API only, start: migrate then serve",
    )
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

        run_migrations()
        print("Migrations completed. Starting API server.")
        run_server()
        return 0
    except Exception as exc:  # pylint: disable=broad-exception-caught  # pragma: no cover
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
