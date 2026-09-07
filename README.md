# plex-watchlist-sync

Small, single-user automation for a homelab:

- Add to Plex watchlist → request the movie/show through Scryer.
- Remove from watchlist → unmonitor it in Scryer.
- Add to a configured trash playlist → unmonitor the selected scope and request
  deletion.

**Note:** Media operations belong to Scryer and Weaver.

## Development

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).
Run from the repository root:

```sh
# Apply safe fixes, format app, and build the package
./scripts/build.sh
uv run --locked python -m app
```

## Configuration

Set environment variables before starting the process:

- `CONFIG_DIR`: authentication directory; defaults to `/config` in the container.
  Override it with a writable directory when running locally.
- `LOG_LEVEL`: `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, or `CRITICAL`.
- `SYNC_INTERVAL_SECONDS`: wait after each poll; defaults to `30`, minimum `1`.

## Plex authentication

On first run, open the authorization link printed in the logs and sign in to
Plex. Pairing waits up to two minutes.

Device identity, signing keys, and the token are stored under `CONFIG_DIR/plex`.
Keep this directory private. Saved authentication is reused on subsequent runs;
expiring tokens are refreshed.

To authorize again after revoking access, remove its `token` file and restart.

## Container

From the repository root, build and run in the foreground:

```sh
./scripts/docker.sh
```

Ctrl+C stops the worker. For background operation:

```sh
docker compose -f docker/compose.yaml up --build -d # build and run in background
docker compose -f docker/compose.yaml logs -f       # view logs and pairing link
docker compose -f docker/compose.yaml stop          # stop the worker
```

Keep the `/config` volume to retain Plex authentication across container updates.

For homelab builds, set `build.context` to the repository's HTTPS Git URL with
`#<commit-or-tag>` appended. The included Compose file also accepts this through
`WATCHLIST_SYNC_BUILD_CONTEXT`, defaulting to `..` (the repository root) for local
builds. Keep `build.dockerfile` set to `docker/Dockerfile`.
