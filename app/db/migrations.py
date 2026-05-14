from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.models import Base
from app.db.session import get_engine


def run_migrations(engine: Engine | None = None) -> None:
    db_engine = engine or get_engine()
    Base.metadata.create_all(bind=db_engine)
