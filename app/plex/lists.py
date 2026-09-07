"""Read complete Plex lists and the identities needed to match them to Scryer."""

import logging
from threading import Event
from typing import Any
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError, fromstring

from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
from plexapi.video import Movie, Show
from requests import Session

from app.plex.models import PlexItem
from app.settings import Settings

logger = logging.getLogger(__name__)


class PlexReadError(Exception):
    """A safe explanation for rejecting an incomplete or unsupported Plex read."""


def _check_complete(items: Any, expected: int | None = None) -> None:
    # Use the known membership count, or the pagination count retained by PlexAPI.
    total = expected if expected is not None else items.totalSize
    if total is None:
        total = items.size

    # Reject incomplete reads so missing results cannot be mistaken for list removals.
    if total is None or len(items) != total:
        raise PlexReadError("Plex returned an incomplete list; keeping the previous snapshot.")


def read_watchlist(account: MyPlexAccount) -> list[Movie | Show]:
    """Read all watchlist entries, including unreleased movies and shows."""
    # Include external identifiers for matching against Scryer without relying on titles.
    items: Any = account.watchlist(includeGuids=1)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    # Return only a complete read, leaving the caller's previous snapshot safe on failure.
    _check_complete(items)
    return items  # pyright: ignore[reportUnknownVariableType]


def _external_ids(item: Any) -> dict[str, str]:
    # Split provider GUIDs such as tmdb://123 into the identifiers we can match in Scryer.
    ids: dict[str, str] = {}
    for guid in item.guids:
        source, _, value = guid.id.partition("://")
        if source in {"tmdb", "tvdb", "imdb"} and value:
            ids[source] = value
    return ids


def _item(item: Any, item_id: str | None = None) -> PlexItem:
    # Require a media identity before admitting the item into a snapshot.
    if not isinstance(item.guid, str) or not item.guid:
        raise PlexReadError("Plex item has no GUID; keeping the previous snapshot.")

    # Copy the matching fields, using a server-local key for delete-list membership when supplied.
    return PlexItem(
        id=item_id or item.guid,
        type=item.type,
        title=item.title,
        year=item.year,
        guid=item.guid,
        external_ids=_external_ids(item),
    )


def _connect_server(account: MyPlexAccount, url: str, session: Session) -> PlexServer:
    # Ask the configured server for its identity before selecting an account resource.
    with session.get(f"{url}/identity", timeout=(10, 30), allow_redirects=False) as response:
        if response.status_code != 200:
            raise PlexReadError(f"Plex identity lookup failed (HTTP {response.status_code}).")

        # Decode the machine identifier used to locate this server in the Plex account.
        try:
            server_id = fromstring(response.content).get("machineIdentifier")
        except ParseError:
            raise PlexReadError("Plex server returned an invalid identity response.") from None

    if not server_id:
        raise PlexReadError("Plex server identity is missing its machine identifier.")

    # Connect with the resource's server access token, not the account's cloud JWT.
    resource: Any = account.resource(server_id)  # pyright: ignore[reportUnknownMemberType]
    return PlexServer(url, token=resource.accessToken, session=session)


def read_lists(
    account: MyPlexAccount,
    settings: Settings,
    stop: Event,
) -> tuple[dict[str, PlexItem], dict[str, PlexItem]]:
    # Build the cloud snapshot by stable GUID, not titles or list order.
    watchlist: dict[str, PlexItem] = {}
    for item in read_watchlist(account):
        entry = _item(item)

        # Reject unsupported or repeated identities rather than silently losing entries.
        if entry.type not in {"movie", "show"} or not entry.id.startswith("plex://"):
            raise PlexReadError("Unsupported watchlist identity; keeping the previous snapshot.")
        if entry.id in watchlist:
            raise PlexReadError("Plex watchlist repeated an item; keeping the previous snapshot.")

        watchlist[entry.id] = entry

    # Find the configured delete list on the server and require a regular video playlist.
    with Session() as session:
        server: Any = _connect_server(account, str(settings.plex_server_url).rstrip("/"), session)
        playlist = server.playlist(settings.plex_delete_list)
        if playlist is None:
            raise PlexReadError("The configured Plex delete list was not found.")
        if playlist.playlistType != "video" or playlist.smart:
            raise PlexReadError("The delete list must be a regular video playlist.")

        # Read leaf items: Plex expands show and season selections into individual episodes.
        items = playlist.items()
        _check_complete(items, playlist.leafCount)

        # Index local entries by server/rating key and reuse show metadata across episodes.
        delete_list: dict[str, PlexItem] = {}
        shows: dict[str, Any] = {}
        for item in items:
            if stop.is_set():
                raise InterruptedError("Plex list read cancelled")

            # Reject remote entries: their rating keys belong to a different server.
            source = getattr(item, "sourceURI", None)
            if source and urlsplit(source).netloc != server.machineIdentifier:  # pyright: ignore[reportUnknownMemberType]
                raise PlexReadError(
                    "Delete-list entries must belong to the configured Plex server."
                )
            entry = _item(item, f"{server.machineIdentifier}/{item.ratingKey}")

            # Attach the parent show's identifiers and episode coordinates for Scryer matching.
            if entry.type == "episode":
                show_key = str(item.grandparentRatingKey)
                if show_key not in shows:
                    shows[show_key] = item.show()

                show = shows[show_key]
                entry.show_guid = show.guid
                entry.show_title = show.title
                entry.show_external_ids = _external_ids(show)
                entry.season = item.parentIndex
                entry.episode = item.index

            delete_list[entry.id] = entry

        # Read each represented show's local episodes to establish the deletion-scope totals.
        for show in shows.values():
            if stop.is_set():
                raise InterruptedError("Plex membership read cancelled")

            episodes = show.episodes()
            _check_complete(episodes, show.leafCount)

            # Group local episode IDs by season, without assuming external catalog completeness.
            seasons: dict[int, set[str]] = {}
            for episode in episodes:
                seasons.setdefault(episode.parentIndex, set()).add(
                    f"{server.machineIdentifier}/{episode.ratingKey}"
                )

            # Show how much of each season is selected, without promoting or deleting it yet.
            for season, member_ids in seasons.items():
                selected = len(member_ids & delete_list.keys())
                if selected:
                    logger.info(
                        "Delete-list scope: %s season=%s selected=%d/library=%d show_library=%d",
                        show.title,
                        season,
                        selected,
                        len(member_ids),
                        len(episodes),
                    )

    return watchlist, delete_list
