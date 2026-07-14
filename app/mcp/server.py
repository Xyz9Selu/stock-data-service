"""stdio MCP server for stock-data-service (agent-facing tools).

Run:
  STOCK_DATA_API=http://127.0.0.1:8002 python -m app.mcp.server

OpenCode / Claude Desktop example:
  command: ["uv", "run", "--directory", "/home/xyz/stock-data-service", "python", "-m", "app.mcp.server"]
  env: STOCK_DATA_API=http://127.0.0.1:8002
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp.client import StockDataHttpClient, clip_rows

mcp = FastMCP(
    "stock-data-service",
    instructions=(
        "A-share market data via stock-data-service (Tushare + disk cache). "
        "Prefer cache-friendly calls; report_rc is rate-limited (~1/min live). "
        "ts_code format: 600160.SH / 000001.SZ / 688498.SH."
    ),
)

_client = StockDataHttpClient()


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


@mcp.tool()
def health() -> str:
    """Check stock-data-service health, DB status, token, and cache stats."""
    return _json(_client.healthz())


@mcp.tool()
def cache_stats() -> str:
    """Return on-demand query disk cache statistics."""
    return _json(_client.cache_stats())


@mcp.tool()
def fina_mainbz(ts_code: str, type: str = "P", force_refresh: bool = False, max_rows: int = 50) -> str:
    """Segment revenue (主营构成) for a stock. type: P=product, D=region/area.

    Args:
        ts_code: e.g. 600160.SH
        type: P (product) or D (region)
        force_refresh: bypass disk cache
        max_rows: max rows returned to the agent
    """
    data = _client.fina_mainbz(ts_code=ts_code, type=type, force_refresh=force_refresh)
    return _json(clip_rows(data, max_rows=max_rows))


@mcp.tool()
def report_rc(
    ts_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    force_refresh: bool = False,
    max_rows: int = 30,
) -> str:
    """Sell-side research reports (券商研报). Live fetch ~1/min; use cache when possible.

    Args:
        ts_code: e.g. 688498.SH
        start_date: YYYYMMDD
        end_date: YYYYMMDD
        force_refresh: bypass disk cache (slow / rate-limited)
        max_rows: max rows returned
    """
    data = _client.report_rc(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        force_refresh=force_refresh,
    )
    return _json(clip_rows(data, max_rows=max_rows))


@mcp.tool()
def daily_basic(
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    force_refresh: bool = False,
    max_rows: int = 50,
) -> str:
    """Daily valuation metrics (PE/PB/total_mv/circ_mv/turnover etc.).

    Args:
        ts_code: optional stock code
        trade_date: single day YYYYMMDD
        start_date / end_date: range YYYYMMDD
    """
    data = _client.daily_basic(
        ts_code=ts_code,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
        force_refresh=force_refresh,
    )
    return _json(clip_rows(data, max_rows=max_rows))


@mcp.tool()
def stock_company(ts_code: str, force_refresh: bool = False) -> str:
    """Company profile: chairman, main_business, business_scope."""
    return _json(_client.stock_company(ts_code=ts_code, force_refresh=force_refresh))


@mcp.tool()
def tushare_query(
    api_name: str,
    params_json: str = "{}",
    force_refresh: bool = False,
    max_rows: int = 50,
) -> str:
    """Generic Tushare Pro API call with disk cache.

    Args:
        api_name: e.g. moneyflow, balancesheet, income, daily, trade_cal
        params_json: JSON object of API params, e.g. '{"ts_code":"600160.SH"}'
        force_refresh: bypass cache
        max_rows: max rows returned
    """
    try:
        params = json.loads(params_json) if params_json else {}
        if not isinstance(params, dict):
            return _json({"error": "params_json must be a JSON object"})
    except json.JSONDecodeError as e:
        return _json({"error": f"invalid params_json: {e}"})
    data = _client.tushare(api_name, params=params, force_refresh=force_refresh)
    return _json(clip_rows(data, max_rows=max_rows))


@mcp.tool()
def sync_status() -> str:
    """PostgreSQL full-market sync status (running / last date / pending)."""
    return _json(_client.sync_status())


@mcp.tool()
def sync_trigger() -> str:
    """Trigger a background full-market data sync job (202 Accepted)."""
    return _json(_client.sync_trigger())


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
