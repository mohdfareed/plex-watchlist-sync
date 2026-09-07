"""Initialize the application and report its exit status."""

import logging

from pydantic import ValidationError

from app.plex.auth import AuthenticationError
from app.plex.events import ChangeDetector, StateError
from app.settings import load_settings
from app.sync import sync_plex
from app.worker import run

logger = logging.getLogger(__package__)


def main() -> int:
    try:  # Load and validate settings.
        settings = load_settings(logger)
    except ValidationError, OSError:
        return 1

    try:  # Run the main worker.
        changes = ChangeDetector(settings.config_dir / "state.json")
        run(lambda stop: sync_plex(settings, stop, changes), settings)

    # Report actionable authentication/state failures without exposing credentials.
    except (AuthenticationError, StateError) as error:
        logger.error("%s", error)
        return 1

    # Report fatal errors without exposing request URLs, tokens, or response bodies.
    except Exception as error:
        logger.error("Worker failed (%s).", type(error).__name__)
        return 1

    # Cover Ctrl+C outside the worker's signal-handling window.
    except KeyboardInterrupt:
        logger.info("Stopped.")
        return 130

    return 0  # Controlled shutdown without error.


if __name__ == "__main__":
    raise SystemExit(main())
