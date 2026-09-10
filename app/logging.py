"""Rich console output and bounded, plain-text logs beside the saved state."""

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text
from rich.traceback import Traceback

# =============================================================================
# MARK: Logging setup
# =============================================================================


def setup_console_logging() -> RichHandler:
    """Configure Rich console logs and suppress sensitive library diagnostics."""
    # Treat media titles as text, not Rich markup; never install rich tracebacks.
    console = Console(file=sys.stdout)
    # Text's overflow setting alone does not disable Console.print's final crop.
    console.soft_wrap = not console.is_terminal
    handler = _ConsoleLogHandler(
        level=logging.INFO,
        console=console,
        omit_repeated_times=False,
        show_path=False,
        markup=False,
        keywords=[],
    )
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logging.basicConfig(level=logging.DEBUG, handlers=[handler], force=True)

    # DEBUG file logging must not enable sensitive library HTTP/auth diagnostics.
    logging.getLogger("plexapi").disabled = True
    logging.getLogger("requests").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    return handler


def setup_file_logging(config_dir: Path) -> None:
    """Add rotating plain-text DEBUG logs under the configuration directory."""
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


# =============================================================================
# MARK: Console rendering
# =============================================================================


# Keep redirected records intact without Rich's width-constrained table.
class _ConsoleLogHandler(RichHandler):
    def render_message(self, record: logging.LogRecord, message: str) -> ConsoleRenderable:
        """Render redirected messages as literal single-line text."""
        if self.console.is_terminal:
            return super().render_message(record, message)

        # Include ordinary exception/stack text without introducing extra log lines.
        message = message.replace("\r", r"\r").replace("\n", r"\n")
        return Text(message, no_wrap=True, overflow="ignore")

    def render(
        self,
        *,
        record: logging.LogRecord,
        traceback: Traceback | None,
        message_renderable: ConsoleRenderable,
    ) -> ConsoleRenderable:
        """Use Rich's interactive layout only when attached to a terminal."""
        if self.console.is_terminal:
            return super().render(
                record=record, traceback=traceback, message_renderable=message_renderable
            )

        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        return Text(
            f"{timestamp} {record.levelname:<8} {message_renderable}",
            no_wrap=True,
            overflow="ignore",
        )
