from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from app.config import Settings

API_TTL_HOURS: dict[str, float | None] = {
    "daily_basic": 12,
    "daily": 12,
    "fina_mainbz": 168,
    "stock_company": 168,
    "fina_indicator": 72,
    "income": 72,
    "balancesheet": 72,
    "cashflow": 72,
    "forecast": 24,
    "express": 24,
    "report_rc": 48,
    "moneyflow": 12,
    "top10_holders": 168,
    "stock_basic": 168,
    "trade_cal": 720,
    "broker_recommend": 168,
}


def _stable_key(api: str, params: dict[str, Any]) -> str:
    items = sorted((k, "" if v is None else str(v)) for k, v in params.items())
    raw = api + "|" + json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


class CacheStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.root = Path(self.settings.data_root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, api: str, params: dict[str, Any]) -> Path:
        key = _stable_key(api, params)
        d = self.root / api
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{key}.json"

    def get(
        self,
        api: str,
        params: dict[str, Any],
        ttl_hours: float | None = ...,  # type: ignore[assignment]
    ) -> dict[str, Any] | None:
        path = self.path_for(api, params)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if ttl_hours is ...:
            ttl_hours = API_TTL_HOURS.get(api, self.settings.cache_ttl_hours)
        if ttl_hours is not None:
            age_h = (time.time() - float(payload.get("fetched_at") or 0)) / 3600.0
            if age_h > float(ttl_hours):
                return None
        payload["cache_hit"] = True
        payload["cache_path"] = str(path)
        return payload

    def set(
        self,
        api: str,
        params: dict[str, Any],
        rows: list[dict],
        meta: dict | None = None,
    ) -> dict[str, Any]:
        path = self.path_for(api, params)
        payload = {
            "api": api,
            "params": params,
            "fetched_at": time.time(),
            "fetched_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "n_rows": len(rows),
            "rows": rows,
            "meta": meta or {},
            "cache_hit": False,
            "cache_path": str(path),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        return payload

    def stats(self) -> dict[str, Any]:
        by_api: dict[str, int] = {}
        total_bytes = 0
        total_files = 0
        if not self.root.exists():
            return {"root": str(self.root), "files": 0, "bytes": 0, "by_api": {}}
        for p in self.root.rglob("*.json"):
            total_files += 1
            total_bytes += p.stat().st_size
            api = p.parent.name
            by_api[api] = by_api.get(api, 0) + 1
        return {
            "root": str(self.root),
            "files": total_files,
            "bytes": total_bytes,
            "by_api": by_api,
        }

    def purge(self, api: str | None = None, older_than_hours: float | None = None) -> int:
        removed = 0
        paths = (
            list((self.root / api).glob("*.json"))
            if api
            else list(self.root.rglob("*.json"))
        )
        now = time.time()
        for p in paths:
            if older_than_hours is not None:
                if (now - p.stat().st_mtime) / 3600.0 < older_than_hours:
                    continue
            try:
                p.unlink()
                removed += 1
            except OSError:
                pass
        return removed
