"""Business logic for each Plex synchronization attempt."""

import logging
from threading import Event

from plexapi.exceptions import PlexApiException
from requests import RequestException

from app.plex.auth import with_authentication
from app.plex.lists import read_watchlist
from app.settings import Settings

logger = logging.getLogger(__name__)


def sync_plex(settings: Settings, stop: Event) -> None:
    """Run a single iteration of the Plex polling loop."""
    try:
        watchlist = with_authentication(settings, read_watchlist, stop)

    # Handle Plex API and network errors.
    except (PlexApiException, RequestException) as error:
        if stop.is_set():
            return

        # Library exception messages can contain credentials or response bodies.
        logger.error(
            "Plex poll failed (%s); retrying in %g seconds.",
            type(error).__name__,
            settings.sync_interval_seconds,
        )
        return  # Try again on the next iteration.

    # Log the watchlist entries.
    for item in watchlist:
        logger.info(
            "%s: %s (%s)",
            item.type,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            item.title,  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
            item.year or "unknown year",  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        )
