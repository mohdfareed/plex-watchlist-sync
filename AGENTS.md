# Working agreement

## Scope and budget

- One user, infrequent use, a small homelab automation—not a framework.
- Two-hour implementation budget; ten hours of lifetime maintenance.
- Work in small increments. Stop for feedback after each agreed checkpoint.
- No automated tests, test dependencies, or scaffolding unless requested.
- Use uv and Ruff. Validate with lint/format checks, builds, and manual checks.
- Compose builds directly from Git. No registry or publishing pipeline.
- The tool is named `watchlist-sync`; its Python package lives in `app/`.
  Keep container files at `docker/` and use the `python -m app` entrypoint.
- Docker runs as UID/GID 10001 with persistent authentication in `/config`.
  No media mounts or inbound ports.
- Do not deploy, publish, or mutate live service data without explicit approval.

## Behavior

- Watchlist addition → request and monitor the entire exposed movie/show in
  Scryer.
- Watchlist removal → unmonitor; do not explicitly cancel downloads or delete
  files.
- Delete-list addition → unmonitor the scope and request deletion.
- Process existing contents on every startup, then poll for list changes.
  Also compare saved snapshots to detect net removals made while stopped.
- A small Plex change detector compares snapshots and emits item-specific
  events: watchlist additions/removals and delete-list additions.
- Watchlist additions have a grace period, tracked by stable item ID. Removal
  during the grace period cancels the pending addition. Use
  `WATCHLIST_GRACE_SEC=60` by default, including startup contents. Preserve
  pending deadlines across restarts and check membership before releasing them.
- Persist the last snapshots and pending watchlist addition deadlines together
  in `/config/state.json`. Save atomically after successful event handling;
  failures retain the previous baseline for retry. No activity history or
  action journal.
- Plex is the event source. Query and write to Scryer as needed to handle
  events; do not build a Scryer snapshot/event loop or a generic event-bus
  framework.
- No continuous enforcement, blanket episode resets, or list-priority machinery.
- Complete delete-list selections may become season/show operations based on
  current Plex membership.
- Delegate media operations to Scryer/Weaver. Never delete files directly.
- Future services are not requirements. Confirm behavioral departures first.

## Code and documentation

- Organize by concrete responsibility. No speculative interfaces or wrappers.
- Keep `worker.py` limited to app lifecycle plumbing. Put sync business logic in
  `sync.py` and wire it into the worker in `__main__.py`.
- Use descriptive names, type hints, guard clauses, and a readable happy path.
- Separate meaningful steps with whitespace and recipe-style comments.
- Keep code within 100 columns and Markdown within 80. Keep files small.
- Prefer service defaults. Mark provisional policy with `# REVIEW:` comments.
- Every dependency, configuration rule, and paragraph must serve a current need.
- Judge every addition by lifetime maintenance cost, not ease of writing it.
  If its value is uncertain, ask before adding it.
- Document usage, not development status, publishing reminders, or
  hypotheticals. Change README only when needed to configure, run, or use the
  tool—not automatically after each task. Keep implementation details here or
  in code.
- Use Rich console logging and rotating plain-text DEBUG logs under
  `CONFIG_DIR`, following `machine`'s 10 MiB / three-backup limits. No Rich
  traceback setup.
- Keep this file and README consistent. Never log credentials.
