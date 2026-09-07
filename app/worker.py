"""Run the worker until shutdown is requested."""

import logging
import signal
from threading import Event
from typing import Callable

from app.settings import Settings

logger = logging.getLogger(__name__)


def run(func: Callable[[Event], None], settings: Settings) -> None:
    """Call the application's work each interval until shutdown is requested."""
    stop = Event()
    handlers = {signum: signal.getsignal(signum) for signum in (signal.SIGINT, signal.SIGTERM)}

    try:
        # Request a cooperative stop so active work can finish and release its resources.
        for signum in handlers:
            signal.signal(signum, lambda _, __: stop.set())
        logger.info("Worker started; loop interval is %g seconds.", settings.sync_interval_sec)

        # Run the work until shutdown is requested.
        while not stop.is_set():
            func(stop)
            if stop.is_set():
                break
            stop.wait(settings.sync_interval_sec)

    # Work may unwind early with InterruptedError after shutdown is requested.
    except InterruptedError:
        if not stop.is_set():
            raise

    finally:  # Cleanup.
        for signum, handler in handlers.items():
            signal.signal(signum, handler)
        logger.info("Worker stopped.")
