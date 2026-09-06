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

## Container

```sh
docker compose -f docker/compose.yaml build
docker compose -f docker/compose.yaml run --rm watchlist-sync
```

Keep the `/config` volume to retain Plex authentication across container updates.

For homelab builds, set `build.context` to the repository's HTTPS Git URL with
`#<commit-or-tag>` appended. The included Compose file also accepts this through
`WATCHLIST_SYNC_BUILD_CONTEXT`, defaulting to `..` (the repository root) for local
builds. Keep `build.dockerfile` set to `docker/Dockerfile`.
