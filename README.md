# Plex watchlist sync

Small, single-user automation for a homelab:

- Add to Plex watchlist → request the movie/show through Scryer.
- Remove from watchlist → unmonitor it in Scryer.
- Add to a configured trash playlist → unmonitor the selected scope and request
  deletion.

**Note:** Media operations belong to Scryer and Weaver.

## Development

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync --locked
uv run --locked python -m watchlist_sync
uv run --locked ruff check .
uv run --locked ruff format --check .
uv build
```
