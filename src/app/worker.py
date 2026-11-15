"""Dedicated notification scheduler/queue worker.

Run with ``python -m app.worker``. The web process should set
``RUN_SCHEDULER=false`` so only this process owns cron jobs and the async
dispatch queue.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

from app.api.http import _build_context  # shared context wiring; no web server is started
from app.modules.integration.persistence import JsonFileStore

logger = logging.getLogger("app.worker")


def build_worker_context() -> Any:
    """Build the same AppContext as the API without starting FastAPI."""
    return _build_context(JsonFileStore())


async def run_worker() -> None:
    context = build_worker_context()
    scheduler = context.scheduler_service
    if scheduler is None:
        raise RuntimeError("scheduler_service_not_initialized")
    scheduler.start()
    logger.info("notification worker started")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover - Windows fallback
            pass
    try:
        await stop.wait()
    finally:
        scheduler.stop()
        logger.info("notification worker stopped")


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
