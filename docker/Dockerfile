FROM python:3.14-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /bin/uv

# Copy and build app.
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY app/ app/
RUN uv sync --locked --no-dev --no-editable --no-cache

# Keep credentials writable without running the application as root.
RUN install -d -m 700 -o 10001 -g 10001 /config
USER 10001:10001

ENTRYPOINT ["/app/.venv/bin/python", "-u", "-m", "app"]
