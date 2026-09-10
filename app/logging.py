"""Rich console output and bounded, plain-text logs beside the saved state."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


def setup_console_logging() -> RichHandler:
    # Treat media titles as text, not Rich markup; never install rich tracebacks.
    handler = RichHandler(
        level=logging.INFO,
        console=Console(file=sys.stdout),
        show_path=False,
        markup=False,
        keywords=[],
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.basicConfig(level=logging.DEBUG, handlers=[handler], force=True)

    # DEBUG file logging must not enable sensitive library HTTP/auth diagnostics.
    logging.getLogger("plexapi").disabled = True
    logging.getLogger("requests").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    return handler


def setup_file_logging(config_dir: Path) -> None:
    # Match machine's rotation limits so a long-running worker cannot fill the volume.
    config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        config_dir / "watchlist-sync.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.getLogger().addHandler(handler)
