"""Detect Plex changes and retain snapshots and grace deadlines across restarts."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, FiniteFloat, ValidationError

from app.plex.models import PlexItem

logger = logging.getLogger(__name__)


class StateError(Exception):
    """A state failure with a message safe to log."""


class _State(BaseModel):
    watchlist: dict[str, PlexItem] = Field(default_factory=dict)
    pending: dict[str, FiniteFloat] = Field(default_factory=dict)
    delete_list: dict[str, PlexItem] = Field(default_factory=dict)


@dataclass(frozen=True)
class PlexEvent:
    kind: Literal["watchlist_added", "watchlist_removed", "delete_list_added"]
    item: PlexItem


class ChangeDetector:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.startup = True  # Whether this is the first run.
        self.state = _State()

        # A missing file is a first run; unreadable state must not silently reset history.
        try:
            self.state = _State.model_validate_json(path.read_text())
        except FileNotFoundError:
            pass
        except OSError, ValidationError:
            raise StateError(
                "Cannot load state.json; restore it or remove it to start fresh."
            ) from None

    def prepare(
        self,
        watchlist: dict[str, PlexItem],
        delete_list: dict[str, PlexItem],
        grace_seconds: float,
        now: float,
    ) -> tuple[_State, list[PlexEvent]]:
        """Prepare events without consuming them; commit only after handling succeeds."""
        events: list[PlexEvent] = []
        pending = self.state.pending.copy()

        # Apply observed removals before considering any grace deadline.
        for item_id in self.state.watchlist.keys() - watchlist.keys():
            pending.pop(item_id, None)
            events.append(PlexEvent("watchlist_removed", self.state.watchlist[item_id]))

        # Replay all current entries on startup; otherwise select only newly observed IDs.
        additions = (
            watchlist.keys() if self.startup else watchlist.keys() - self.state.watchlist.keys()
        )

        # Start the grace period for new additions without extending saved deadlines on restart.
        for item_id in additions:
            pending.setdefault(item_id, now + grace_seconds)

        # Recheck current membership so removed items cannot become requests after the delay.
        for item_id, deadline in list(pending.items()):
            if item_id not in watchlist:
                del pending[item_id]
                continue
            if now < deadline:
                continue

            # Grace period elapsed; release the addition and remove it from pending.
            events.append(PlexEvent("watchlist_added", watchlist[item_id]))
            del pending[item_id]

        # Delete-list additions have no grace period; replay current contents on startup too.
        additions = (
            delete_list.keys()
            if self.startup
            else delete_list.keys() - self.state.delete_list.keys()
        )

        events.extend(PlexEvent("delete_list_added", delete_list[item_id]) for item_id in additions)

        # Stage the next baseline without consuming events; the caller commits after success.
        return _State(watchlist=watchlist, delete_list=delete_list, pending=pending), events

    def commit(self, state: _State) -> None:
        """Save successful work atomically, then advance the in-memory baseline."""
        if self.startup or state != self.state:
            try:
                self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                temporary_path = self.path.with_suffix(".tmp")
                temporary_path.write_text(state.model_dump_json(indent=2))
                temporary_path.chmod(0o600)
                temporary_path.replace(self.path)

            # Failed to update sync state.
            except OSError:
                raise StateError(
                    "Cannot save state.json; previous state was not advanced."
                ) from None

        # Make grace-period scheduling and cancellation visible without an activity journal.
        for item_id in state.pending.keys() - self.state.pending.keys():
            logger.info("Watchlist addition waiting for grace period: %s", item_id)
        for item_id in self.state.pending.keys() - state.watchlist.keys():
            logger.info("Pending watchlist addition cancelled: %s", item_id)

        self.state = state
        self.startup = False
