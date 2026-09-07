"""Selected fields from the Scryer v0.19.12 schema, with snake_case names.

Facet values are movie/tv/anime; other enum values retain Scryer's wire spelling.
Nullable fields are required in responses: missing data must not look like absence.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel


def _normalize_facet(value: object) -> object:
    if isinstance(value, str):
        return {"MOVIE": "movie", "SERIES": "tv", "ANIME": "anime"}.get(value, value)
    return value


type Facet = Annotated[Literal["movie", "tv", "anime"], BeforeValidator(_normalize_facet)]
type RequestStatus = Literal["PENDING", "APPROVED", "REJECTED", "CANCELED"]
type MonitorType = Literal[
    "MONITORED",
    "UNMONITORED",
    "FUTURE_EPISODES",
    "MISSING_AND_FUTURE_EPISODES",
    "ALL_EPISODES",
    "ADVANCED",
    "NONE",
]


class _Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, strict=True, hide_input_in_errors=True
    )


class ExternalId(_Model):
    source: str
    value: str


class EpisodeAvailability(_Model):
    state: Literal["AVAILABLE", "PENDING_SCAN", "SCAN_FAILED", "MISSING", "UNMONITORED"]
    primary_quality_label: str | None


class Episode(_Model):
    id: str
    season_number: str | None
    episode_number: str | None
    monitored: bool
    media_availability: EpisodeAvailability


class Collection(_Model):
    id: str
    collection_type: Literal["SEASON", "MOVIE", "ARC", "SPECIALS"]
    collection_index: str
    monitored: bool
    episodes: list[Episode]


class MediaFile(_Model):
    """File evidence, not a derived playable/complete flag; paths are not queried."""

    id: str
    episode_id: str | None
    series_movie_link_ids: list[str]
    role: str
    scan_status: str
    quality_label: str | None


class SeriesMovieLink(_Model):
    id: str
    monitored: bool
    metadata_active: bool


class Title(_Model):
    id: str
    library_id: str
    name: str
    facet: Facet
    external_ids: list[ExternalId]
    monitored: bool
    monitor_type: MonitorType | None
    media_files: list[MediaFile]
    collections: list[Collection]
    series_movie_links: list[SeriesMovieLink]


class MediaRequest(_Model):
    """Approval lifecycle is separate from download or media availability."""

    id: str
    library_id: str
    title: str
    facet: Facet
    external_ids: list[ExternalId]
    status: RequestStatus
    created_title_id: str | None
    requested_monitor_type: MonitorType | None
