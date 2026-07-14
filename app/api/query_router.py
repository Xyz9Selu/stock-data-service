from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import Settings
from app.query.cache_store import CacheStore
from app.query.service import QueryService

router = APIRouter(tags=["query-cache"])

_settings = Settings()
_cache = CacheStore(_settings)
_service: QueryService | None = None


def get_service() -> QueryService:
    global _service
    if _service is None:
        try:
            _service = QueryService(_settings, _cache)
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
    return _service


class QueryBody(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)
    force_refresh: bool = False
    ttl_hours: float | None = None


@router.get("/v1/cache/stats")
def cache_stats() -> dict[str, Any]:
    return _cache.stats()


@router.delete("/v1/cache")
def cache_purge(
    api: str | None = None,
    older_than_hours: float | None = None,
) -> dict[str, Any]:
    n = _cache.purge(api=api, older_than_hours=older_than_hours)
    return {"removed": n, "stats": _cache.stats()}


@router.post("/v1/tushare/{api_name}")
def tushare_post(api_name: str, body: QueryBody) -> dict[str, Any]:
    try:
        return get_service().query(
            api_name,
            body.params,
            force_refresh=body.force_refresh,
            ttl_hours=body.ttl_hours if body.ttl_hours is not None else ...,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/v1/tushare/{api_name}")
def tushare_get(
    api_name: str,
    force_refresh: bool = False,
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str | None = None,
    type: str | None = None,
    fields: str | None = None,
    limit: int | None = None,
    symbol: str | None = None,
    month: str | None = None,
) -> dict[str, Any]:
    params = {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "start_date": start_date,
        "end_date": end_date,
        "period": period,
        "type": type,
        "fields": fields,
        "limit": limit,
        "symbol": symbol,
        "month": month,
    }
    try:
        return get_service().query(api_name, params, force_refresh=force_refresh)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/v1/report_rc")
def report_rc(
    ts_code: str = Query(...),
    start_date: str | None = None,
    end_date: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    return get_service().query(
        "report_rc",
        {"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        force_refresh=force_refresh,
    )


@router.get("/v1/fina_mainbz")
def fina_mainbz(
    ts_code: str = Query(...),
    type: str = "P",
    force_refresh: bool = False,
) -> dict[str, Any]:
    return get_service().query(
        "fina_mainbz",
        {"ts_code": ts_code, "type": type},
        force_refresh=force_refresh,
    )


@router.get("/v1/daily_basic")
def daily_basic(
    ts_code: str | None = None,
    trade_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    return get_service().query(
        "daily_basic",
        {
            "ts_code": ts_code,
            "trade_date": trade_date,
            "start_date": start_date,
            "end_date": end_date,
        },
        force_refresh=force_refresh,
    )


@router.get("/v1/stock_company")
def stock_company(ts_code: str = Query(...), force_refresh: bool = False) -> dict[str, Any]:
    return get_service().query(
        "stock_company",
        {"ts_code": ts_code, "fields": "ts_code,chairman,main_business,business_scope"},
        force_refresh=force_refresh,
    )


@router.get("/v1/batch/report_rc")
def batch_report_rc(
    ts_codes: str = Query(..., description="Comma-separated ts_codes"),
    start_date: str | None = None,
    end_date: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    codes = [c.strip() for c in ts_codes.split(",") if c.strip()]
    svc = get_service()
    out: dict[str, Any] = {}
    for code in codes:
        try:
            out[code] = svc.query(
                "report_rc",
                {"ts_code": code, "start_date": start_date, "end_date": end_date},
                force_refresh=force_refresh,
            )
        except Exception as e:
            out[code] = {"error": str(e), "ts_code": code}
    return {"n": len(codes), "data": out}
