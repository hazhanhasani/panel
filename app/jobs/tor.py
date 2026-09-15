import asyncio

from app import on_shutdown, on_startup
from app.db import GetDB
from app.operation.tor import tor_operation
from app.utils.logger import get_logger

logger = get_logger("tor-reconciliation-job")
_task: asyncio.Task | None = None


async def _loop() -> None:
    # Startup recovery is registered in TorOperation; delay this loop so node/core
    # startup does not create a second simultaneous reconciliation wave.
    await asyncio.sleep(15)
    while True:
        interval = 60
        try:
            async with GetDB() as db:
                settings = await tor_operation.get_settings(db)
                interval = max(15, int(settings.health_check_interval))
                if settings.feature_enabled:
                    await tor_operation.reconcile_all(db, actor="scheduled_reconciliation")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled Tor reconciliation failed")
        await asyncio.sleep(interval)


@on_startup
async def start_tor_reconciliation_job() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop(), name="bluepanel-tor-reconcile")


@on_shutdown
async def stop_tor_reconciliation_job() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None
