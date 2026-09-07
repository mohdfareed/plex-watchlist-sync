"""Business logic for each Plex synchronization attempt."""

import logging
from threading import Event
from time import time

from plexapi.exceptions import PlexApiException
from requests import RequestException

from app.plex.auth import with_authentication
from app.plex.events import ChangeDetector
from app.plex.lists import PlexReadError, read_lists
from app.plex.models import PlexItem
from app.scryer import ScryerClient, ScryerError, get_version, list_media_requests, list_titles
from app.settings import Settings

logger = logging.getLogger(__name__)


def sync_plex(settings: Settings, stop: Event, changes: ChangeDetector) -> None:
    """Read Plex, prepare events, and inspect Scryer without changing either service."""
    try:
        watchlist, delete_list = with_authentication(
            settings, lambda account: read_lists(account, settings, stop), stop
        )
    except PlexReadError as error:
        logger.error("%s", error)
        return

    # Handle Plex API and network errors.
    except (PlexApiException, RequestException) as error:
        if stop.is_set():
            return

        # Library exception messages can contain credentials or response bodies.
        logger.error(
            "Plex poll failed (%s); retrying in %g seconds.",
            type(error).__name__,
            settings.sync_interval_sec,
        )
        return  # Try again on the next iteration.

    # Log the watchlist entries.
    for item in watchlist.values():
        logger.info(
            "%s: %s (%s)",
            item.type,
            item.title,
            item.year or "unknown year",
        )

    # Re-read current membership before releasing additions whose grace period has elapsed.
    state, events = changes.prepare(watchlist, delete_list, settings.watchlist_grace_sec, time())
    if stop.is_set():
        return

    # Scryer is a lookup target: inspect it on startup/events, never on its own polling loop.
    if changes.startup or events:
        try:
            targets = {event.item.id: event.item for event in events}
            targets.update(watchlist)
            targets.update(delete_list)
            _inspect_scryer(settings, stop, list(targets.values()))
        except ScryerError as error:
            logger.error("%s Previous Plex state retained for retry.", error)
            return
    if stop.is_set():
        return

    for event in events:
        logger.info("Plex event %s: %s (id=%s)", event.kind, event.item.title, event.item.id)

    # Logging is the event handler at this checkpoint. Failed reads do not consume events.
    changes.commit(state)


def _inspect_scryer(settings: Settings, stop: Event, plex_items: list[PlexItem]) -> None:
    # Complete the reads before logging a partial catalog as if it were authoritative.
    with ScryerClient(
        f"{str(settings.scryer_url).rstrip('/')}/graphql", settings.scryer_api_key
    ) as client:
        version = get_version(client)
        titles = list_titles(client, stop=stop)
        if stop.is_set():
            raise InterruptedError("Scryer diagnostic read cancelled")
        requests = list_media_requests(client)

    logger.info(
        "Scryer %s: %d managed titles, %d request records visible to this API key.",
        version,
        len(titles),
        len(requests),
    )
    for title in titles:
        logger.info(
            "Scryer title: %s id=%s library=%s facet=%s ids=%s monitored=%s policy=%s files=%d",
            title.name,
            title.id,
            title.library_id,
            title.facet,
            {entry.source: entry.value for entry in title.external_ids},
            title.monitored,
            title.monitor_type,
            len(title.media_files),
        )
        for collection in title.collections:
            logger.info(
                "Scryer collection: title=%s id=%s scope=%s/%s "
                "monitored=%s episodes=%d available=%d",
                title.id,
                collection.id,
                collection.collection_type,
                collection.collection_index,
                collection.monitored,
                len(collection.episodes),
                sum(
                    episode.media_availability.state == "AVAILABLE"
                    for episode in collection.episodes
                ),
            )
            for episode in collection.episodes:
                logger.debug(
                    "Scryer episode: id=%s season=%s episode=%s monitored=%s availability=%s",
                    episode.id,
                    episode.season_number,
                    episode.episode_number,
                    episode.monitored,
                    episode.media_availability.state,
                )
        for media_file in title.media_files:
            logger.debug(
                "Scryer file: id=%s title=%s episode=%s scan=%s",
                media_file.id,
                title.id,
                media_file.episode_id,
                media_file.scan_status,
            )

    for request in requests:
        logger.info(
            "Scryer request: %s id=%s library=%s facet=%s ids=%s "
            "status=%s created_title=%s policy=%s",
            request.title,
            request.id,
            request.library_id,
            request.facet,
            {entry.source: entry.value for entry in request.external_ids},
            request.status,
            request.created_title_id,
            request.requested_monitor_type,
        )

    # Show exact-ID matches without treating names or download progress as a policy decision.
    for item in plex_items:
        ids = item.show_external_ids if item.type == "episode" else item.external_ids
        # TMDB movie and series IDs occupy separate namespaces.
        facets = {"movie"} if item.type == "movie" else {"tv", "anime"}
        title_ids = [
            title.id
            for title in titles
            if title.facet in facets
            and any(ids.get(entry.source) == entry.value for entry in title.external_ids)
        ]
        request_ids = [
            request.id
            for request in requests
            if request.facet in facets
            and any(ids.get(entry.source) == entry.value for entry in request.external_ids)
        ]
        logger.info(
            "Plex identity: %s id=%s guid=%s ids=%s season=%s episode=%s titles=%s requests=%s",
            item.title,
            item.id,
            item.show_guid or item.guid,
            ids,
            item.season,
            item.episode,
            title_ids,
            request_ids,
        )
        if not ids:
            logger.warning("Plex item %s has no external IDs; matching is unresolved.", item.id)
