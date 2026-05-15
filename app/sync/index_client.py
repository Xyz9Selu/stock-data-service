from __future__ import annotations

import time
from datetime import date
from typing import Any

import akshare as ak
import pandas as pd


TRACKED_INDICES: list[tuple[str, str, int, int]] = [
    ("000300", "沪深300", 300, 2005),
    ("000905", "中证500", 500, 2007),
    ("000016", "上证50", 50, 2004),
    ("000852", "中证1000", 1000, 2014),
    ("399006", "创业板指", 100, 2010),
    ("000688", "科创50", 50, 2020),
]


def _retry_with_backoff(fn_name: str, max_attempts: int = 3, **kwargs: Any) -> Any:
    delays = (1, 2)
    last_error: Exception | None = None
    for idx in range(max_attempts):
        try:
            return getattr(ak, fn_name)(**kwargs)
        except Exception as exc:
            last_error = exc
            if idx == max_attempts - 1:
                break
            time.sleep(delays[idx] if idx < len(delays) else 4)
    raise RuntimeError(f"akshare {fn_name} failed after {max_attempts} attempts") from last_error


class IndexDataClient:

    @staticmethod
    def fetch_index_cons(symbol: str) -> pd.DataFrame:
        """Current constituents with inclusion dates. Columns: 品种代码, 品种名称, 纳入日期."""
        return _retry_with_backoff("index_stock_cons", symbol=symbol)

    @staticmethod
    def fetch_index_cons_weight_csindex(symbol: str) -> pd.DataFrame:
        """Current constituents with weights from CSI website."""
        return _retry_with_backoff("index_stock_cons_weight_csindex", symbol=symbol)

    @staticmethod
    def fetch_adjust_history_cni(symbol: str) -> pd.DataFrame:
        """Historical adjustments for CNI indices (399*). Columns: 开始日期, 结束日期, 样本代码, 调整类型."""
        return _retry_with_backoff("index_detail_hist_adjust_cni", symbol=symbol)

    @staticmethod
    def fetch_index_cons_csindex(symbol: str) -> pd.DataFrame:
        """Current constituents snapshot from CSI website."""
        return _retry_with_backoff("index_stock_cons_csindex", symbol=symbol)
