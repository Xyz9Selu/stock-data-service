from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.sync.engine import get_runtime_state, get_sync_lock, get_sync_status, run_sync

router = APIRouter()


async def _run_sync_task(job_id: str) -> None:
    lock = get_sync_lock()
    runtime_state = get_runtime_state()
    async with lock:
        runtime_state["running"] = True
        runtime_state["job_id"] = job_id
        try:
            await asyncio.to_thread(run_sync)
        finally:
            runtime_state["running"] = False
            runtime_state["job_id"] = None


@router.post("/sync/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(background_tasks: BackgroundTasks) -> dict[str, str]:
    lock = get_sync_lock()
    if lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "sync_already_running",
                "message": "A sync job is already in progress",
            },
        )
    job_id = str(uuid4())
    background_tasks.add_task(_run_sync_task, job_id)
    return {"job_id": job_id, "status": "started"}


@router.get("/sync/status")
def sync_status() -> dict[str, object]:
    status_obj = get_sync_status()
    return {
        "running": status_obj.running,
        "last_synced_date": status_obj.last_synced_date,
        "pending_dates": status_obj.pending_dates,
        "total_synced_dates": status_obj.total_synced_dates,
    }
