from __future__ import annotations

import time
from datetime import date
from typing import Any

import tushare as ts

from app.config import Settings


class TushareClient:
    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or Settings()
        if not cfg.tushare_token:
            raise ValueError("TUSHARE_TOKEN is required")
        self._api = ts.pro_api(cfg.tushare_token, timeout=10)
        self._last_call_at = 0.0

    def _throttle(self) -> None:
        self._last_call_at = time.monotonic()

    def _call_with_retry(self, fn_name: str, **kwargs: Any) -> Any:
        delays = (0.5, 1)
        last_error: Exception | None = None
        for index in range(3):
            try:
                self._throttle()
                method = getattr(self._api, fn_name)
                return method(**kwargs)
            except Exception as exc:
                last_error = exc
                if index == 2:
                    break
                time.sleep(delays[index])
        raise RuntimeError(f"Tushare call {fn_name} failed after retries") from last_error

    @staticmethod
    def _fmt_day(day: date) -> str:
        return day.strftime("%Y%m%d")

    def fetch_trade_calendar(self, start_date: date, end_date: date) -> Any:
        return self._call_with_retry(
            "trade_cal",
            exchange="SSE",
            start_date=self._fmt_day(start_date),
            end_date=self._fmt_day(end_date),
        )

    def fetch_stock_basic(self, list_status: str) -> Any:
        return self._call_with_retry(
            "stock_basic",
            exchange="",
            list_status=list_status,
            fields=(
                "ts_code,symbol,name,area,industry,market,exchange,list_status,"
                "list_date,delist_date,is_hs"
            ),
        )

    def fetch_daily(self, trade_date: date) -> Any:
        return self._call_with_retry("daily", trade_date=self._fmt_day(trade_date))

    def fetch_daily_basic(self, trade_date: date) -> Any:
        return self._call_with_retry("daily_basic", trade_date=self._fmt_day(trade_date))

    def fetch_adj_factor(self, trade_date: date) -> Any:
        return self._call_with_retry("adj_factor", trade_date=self._fmt_day(trade_date))
