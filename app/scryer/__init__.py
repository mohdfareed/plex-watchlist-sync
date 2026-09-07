"""Read-only Scryer access using an explicit endpoint and API key.

Use ScryerClient as a context manager, then call get_version, list_titles and
list_media_requests. Queries target Scryer v0.19.12; no live version is assumed.
"""

from .client import ScryerClient, ScryerError
from .media import get_version, list_media_requests, list_titles
from .models import (
    Collection,
    Episode,
    EpisodeAvailability,
    ExternalId,
    Facet,
    MediaFile,
    MediaRequest,
    MonitorType,
    RequestStatus,
    SeriesMovieLink,
    Title,
)

__all__ = [
    "Collection",
    "Episode",
    "EpisodeAvailability",
    "ExternalId",
    "Facet",
    "MediaFile",
    "MediaRequest",
    "MonitorType",
    "RequestStatus",
    "ScryerClient",
    "ScryerError",
    "SeriesMovieLink",
    "Title",
    "get_version",
    "list_media_requests",
    "list_titles",
]
