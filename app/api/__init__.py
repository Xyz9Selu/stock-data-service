from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings
from app.db.migrations import run_migrations
from app.db.session import get_engine, ping_database

from .router import router


def create_app() -> FastAPI:
    settings = Settings()
    engine = get_engine(settings)
    app = FastAPI(title="stock-data-service")
    app.include_router(router)

    @app.on_event("startup")
    def startup() -> None:
        run_migrations(engine)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        ping_database(engine)
        return {"status": "ok"}

    return app
