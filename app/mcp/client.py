from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class StockDataHttpClient:
    """Thin HTTP client for the stock-data-service REST API."""

    def __init__(self, base_url: str | None = None, timeout: float = 120.0) -> None:
        self.base_url = (base_url or os.getenv("STOCK_DATA_API", "http://127.0.0.1:8002")).rstrip(
            "/"
        )
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if params:
            q = {k: v for k, v in params.items() if v is not None and v != ""}
            if q:
                url = f"{url}?{urllib.parse.urlencode(q)}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(detail)
            except Exception:
                parsed = {"detail": detail}
            raise RuntimeError(f"HTTP {e.code} {path}: {parsed}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot reach stock-data-service at {self.base_url}: {e.reason}. "
                "Start it with: docker compose up -d"
            ) from e

    def healthz(self) -> dict[str, Any]:
        return self._request("GET", "/healthz")

    def cache_stats(self) -> dict[str, Any]:
        return self._request("GET", "/v1/cache/stats")

    def fina_mainbz(
        self, ts_code: str, type: str = "P", force_refresh: bool = False
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/fina_mainbz",
            params={"ts_code": ts_code, "type": type, "force_refresh": str(force_refresh).lower()},
        )

    def report_rc(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/report_rc",
            params={
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "force_refresh": str(force_refresh).lower(),
            },
        )

    def daily_basic(
        self,
        ts_code: str | None = None,
        trade_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/daily_basic",
            params={
                "ts_code": ts_code,
                "trade_date": trade_date,
                "start_date": start_date,
                "end_date": end_date,
                "force_refresh": str(force_refresh).lower(),
            },
        )

    def stock_company(self, ts_code: str, force_refresh: bool = False) -> dict[str, Any]:
        return self._request(
            "GET",
            "/v1/stock_company",
            params={"ts_code": ts_code, "force_refresh": str(force_refresh).lower()},
        )

    def tushare(
        self,
        api_name: str,
        params: dict[str, Any] | None = None,
        force_refresh: bool = False,
        ttl_hours: float | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "params": params or {},
            "force_refresh": force_refresh,
        }
        if ttl_hours is not None:
            body["ttl_hours"] = ttl_hours
        return self._request("POST", f"/v1/tushare/{api_name}", body=body)

    def sync_status(self) -> dict[str, Any]:
        return self._request("GET", "/sync/status")

    def sync_trigger(self) -> dict[str, Any]:
        return self._request("POST", "/sync/trigger")


def clip_rows(payload: dict[str, Any], max_rows: int = 50) -> dict[str, Any]:
    """Limit rows returned to agents to control context size."""
    out = dict(payload)
    rows = out.get("rows") or out.get("data")
    if isinstance(rows, list) and len(rows) > max_rows:
        out["rows"] = rows[:max_rows]
        out["truncated"] = True
        out["returned_rows"] = max_rows
        out["total_rows"] = out.get("n_rows", len(rows))
        if "data" in out and out["data"] is rows:
            out["data"] = out["rows"]
    return out
