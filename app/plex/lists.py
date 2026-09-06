"""Read the current Plex lists without changing their contents."""

from plexapi.myplex import MyPlexAccount
from plexapi.video import Movie, Show


def read_watchlist(account: MyPlexAccount) -> list[Movie | Show]:
    """Read all watchlist entries, including unreleased movies and shows."""
    return account.watchlist()  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
