"""Load configuration and initialize application logging."""

import logging
import sys

from pydantic import ValidationError

from app.settings import Settings

# read name from pyproject.toml (uv)
app_name = "plex-watchlist-sync"
logger = logging.getLogger(app_name)


def main() -> int:
    # Start logging before validation so configuration failures are visible.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    # Report invalid fields without including their supplied values.
    try:
        settings = Settings()
    except ValidationError as error:
        for issue in error.errors(include_input=False, include_context=False, include_url=False):
            field = ".".join(str(part) for part in issue["loc"]).upper()
            logger.error("%s: %s", field, issue["msg"])
        return 1

    # Configure our verbosity without exposing library HTTP/auth diagnostics.
    logger.setLevel(settings.log_level)
    logging.getLogger("plexapi").disabled = True
    logging.getLogger("requests").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    logger.info(
        "Configuration loaded; polling interval is %g seconds.",
        settings.sync_interval_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
