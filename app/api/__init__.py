from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings
from app.db.migrations import run_migrations
from app.db.session import get_engine, ping_database

from .query_router import router as query_router
from .router import router


def create_app() -> FastAPI:
    settings = Settings()
    engine = get_engine(settings)
    app = FastAPI(
        title="stock-data-service",
        description="A-share data: PG sync + on-demand Tushare disk cache",
    )
    app.include_router(router)
    app.include_router(query_router)

    @app.on_event("startup")
    def startup() -> None:
        run_migrations(engine)

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        db_ok = True
        db_err = None
        try:
            ping_database(engine)
        except Exception as e:  # pragma: no cover
            db_ok = False
            db_err = str(e)
        from app.query.cache_store import CacheStore

        return {
            "status": "ok" if db_ok else "degraded",
            "db_ok": db_ok,
            "db_error": db_err,
            "token_set": bool(settings.tushare_token),
            "data_root": settings.data_root,
            "cache": CacheStore(settings).stats(),
        }

    return app
