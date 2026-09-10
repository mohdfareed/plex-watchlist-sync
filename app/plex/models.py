"""The Plex identity and scope needed to handle list changes."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# MARK: Public models
# =============================================================================


class PlexItem(BaseModel):
    """A Plex item's identity, matching metadata, and optional episode scope."""

    model_config = ConfigDict(hide_input_in_errors=True)

    # Cloud GUIDs identify watchlist entries; server/rating keys identify delete-list entries.
    id: str = Field(min_length=1)
    type: Literal["movie", "show", "episode"]
    title: str
    year: int | None = None
    guid: str
    external_ids: dict[str, str] = Field(default_factory=dict)
    show_guid: str | None = None
    show_title: str | None = None
    show_external_ids: dict[str, str] = Field(default_factory=dict)
    season: int | None = None
    episode: int | None = None


@dataclass(frozen=True)
class PlexLists:
    """Complete watchlist and delete-list snapshots keyed by stable item ID."""

    watchlist: dict[str, PlexItem]
    delete_list: dict[str, PlexItem]
