"""The Plex identity and scope needed to handle list changes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PlexItem(BaseModel):
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
