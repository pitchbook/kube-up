import asyncio

import kopf
from structlog import get_logger

logger = get_logger()


@kopf.on.probe(id="watcher-healthcheck")  # type: ignore[arg-type]
async def check_watchers(**kwargs):
    # Collect asyncio tasks that are responsible for watching kubernetes events
    # if one of these fails, the healthcheck should fail
    watcher_tasks = {task.get_name(): task for task in asyncio.all_tasks() if "watcher for" in task.get_name()}

    for name, task in watcher_tasks.items():
        if task.done():
            exception = task.exception()
            if exception is not None:
                logger.error("watcher failed", watcher=name)
                raise RuntimeError(f"watcher {name} failed: {exception}")

    return ""
