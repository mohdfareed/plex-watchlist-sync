"""Authenticate with Plex and display the current watchlist."""

import logging

from plexapi.exceptions import PlexApiException
from pydantic import ValidationError
from requests import RequestException

from app.plex.auth import AuthenticationError, with_authentication
from app.plex.lists import read_watchlist
from app.settings import load_settings

logger = logging.getLogger(__package__)


def main() -> int:
    try:
        settings = load_settings(logger)
    except ValidationError:
        return 1

    try:
        # Print the Plex scope as supplied, without requesting or changing anything.
        watchlist = with_authentication(settings, read_watchlist)
        for item in watchlist:
            logger.info(
                "%s: %s (%s)",
                item.type,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                item.title,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
                item.year or "unknown year",  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            )

    # Handle authentication failures.
    except AuthenticationError as error:
        logger.error("%s", error)
        return 1

    # Handle library exceptions, hiding request URLs, tokens, or response bodies.
    except (PlexApiException, RequestException, OSError, ValueError) as error:
        logger.error(
            "Plex startup failed (%s). Check connectivity and the authentication directory.",
            type(error).__name__,
        )
        return 1

    # Handle user-initiated termination without a traceback.
    except KeyboardInterrupt:
        logger.info("Stopped.")
        return 130

    return 0  # Controlled shutdown without error.


if __name__ == "__main__":
    raise SystemExit(main())
