from __future__ import annotations

import logging
import threading
import time
from typing import Any

import pandas as pd
import tushare as ts

from app.config import Settings
from app.query.cache_store import CacheStore
from app.query.pg_source import PgSource

logger = logging.getLogger(__name__)

API_MIN_INTERVAL: dict[str, float] = {
    "report_rc": 61.0,
    "stk_surv": 2.0,
}


class QueryService:
    """Rate-limited Tushare on-demand queries with disk cache."""

    def __init__(self, settings: Settings | None = None, cache: CacheStore | None = None) -> None:
        self.settings = settings or Settings()
        if not self.settings.tushare_token:
            raise ValueError("TUSHARE_TOKEN is required")
        ts.set_token(self.settings.tushare_token)
        self._api = ts.pro_api(self.settings.tushare_token)
        self.cache = cache or CacheStore(self.settings)
        self.pg = PgSource(self.settings)
        self._lock = threading.Lock()
        self._last_call: dict[str, float] = {}
        self._last_any = 0.0

    def _throttle(self, api: str) -> None:
        min_iv = API_MIN_INTERVAL.get(api, self.settings.tushare_min_interval)
        if api == "report_rc":
            min_iv = max(min_iv, self.settings.report_rc_interval)
        with self._lock:
            now = time.monotonic()
            g_wait = self.settings.tushare_min_interval - (now - self._last_any)
            a_wait = min_iv - (now - self._last_call.get(api, 0.0))
            wait = max(0.0, g_wait, a_wait)
            if wait > 0:
                time.sleep(wait)
            t2 = time.monotonic()
            self._last_any = t2
            self._last_call[api] = t2

    @staticmethod
    def _df_to_rows(df: Any) -> list[dict]:
        if df is None or not isinstance(df, pd.DataFrame) or len(df) == 0:
            return []
        records = df.where(pd.notnull(df), None).to_dict(orient="records")
        out = []
        for r in records:
            clean = {}
            for k, v in r.items():
                if hasattr(v, "item"):
                    try:
                        v = v.item()
                    except Exception:
                        v = str(v)
                clean[k] = v
            out.append(clean)
        return out

    def query(
        self,
        api: str,
        params: dict[str, Any] | None = None,
        *,
        force_refresh: bool = False,
        ttl_hours: float | None = ...,  # type: ignore[assignment]
    ) -> dict[str, Any]:
        params = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
        if not force_refresh:
            try:
                local = self.pg.query(api, params)
            except Exception:  # DB trouble must not take the endpoint down
                logger.exception("pg source failed for %s, falling back to Tushare", api)
                local = None
            if local is not None:
                return local
            hit = self.cache.get(api, params, ttl_hours=ttl_hours)
            if hit is not None:
                return hit

        self._throttle(api)
        method = getattr(self._api, api, None)
        if method is None:
            raise ValueError(f"Unknown tushare API: {api}")

        last_err: Exception | None = None
        for attempt in range(3):
            try:
                df = method(**params)
                rows = self._df_to_rows(df)
                return self.cache.set(api, params, rows, meta={"attempt": attempt + 1})
            except Exception as e:
                last_err = e
                msg = str(e)
                if "频率" in msg or "限" in msg:
                    time.sleep(API_MIN_INTERVAL.get(api, 5) * (attempt + 1))
                else:
                    time.sleep(0.5 * (attempt + 1))
        raise RuntimeError(f"tushare {api} failed: {last_err}") from last_err
