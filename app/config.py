from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    tushare_token: str = os.getenv("TUSHARE_TOKEN", "")
    postgres_host: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "postgres")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8002"))
    # On-demand query disk cache (report_rc / fina_mainbz / …)
    data_root: str = os.getenv(
        "DATA_ROOT",
        str(_PROJECT_ROOT / "data" / "cache"),
    )
    tushare_min_interval: float = float(os.getenv("TUSHARE_MIN_INTERVAL", "0.35"))
    report_rc_interval: float = float(os.getenv("TUSHARE_REPORT_RC_INTERVAL", "61"))
    cache_ttl_hours: float = float(os.getenv("CACHE_TTL_HOURS", "24"))

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
