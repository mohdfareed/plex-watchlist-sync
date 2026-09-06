"""Verify the packaged runtime without contacting external services."""

from importlib.metadata import version

import jwt
import plexapi
import pydantic_settings
import requests


def main() -> None:
    print("Plex watchlist sync: container foundation ready; synchronization is not implemented.")
    print(
        f"Dependencies loaded: PlexAPI {plexapi.__version__}, PyJWT {jwt.__version__}, "
        f"Requests {version(requests.__name__)}, "
        f"Pydantic Settings {pydantic_settings.__version__}."
    )


if __name__ == "__main__":
    main()
