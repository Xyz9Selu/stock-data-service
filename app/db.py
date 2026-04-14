from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.sql import text

from app.config import Settings


def get_engine(settings: Settings | None = None) -> Engine:
    config = settings or Settings()
    return create_engine(config.sqlalchemy_url, pool_pre_ping=True, future=True)


def ping_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
