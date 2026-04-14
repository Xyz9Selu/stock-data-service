from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings
from app.db import get_engine, ping_database


def create_app() -> FastAPI:
    settings = Settings()
    engine = get_engine(settings)
    app = FastAPI(title="stock-data-service")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        ping_database(engine)
        return {"status": "ok"}

    return app
