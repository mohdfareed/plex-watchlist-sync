"""Browser pairing and saved Plex authentication."""

import logging
from pathlib import Path
from threading import Event
from typing import Callable
from uuid import uuid4

from plexapi.myplex import MyPlexAccount, MyPlexJWTLogin
from requests import Session

from app.settings import Settings

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """An authentication failure with a message safe to log."""


def _load_login(directory: Path, session: Session) -> MyPlexJWTLogin:
    # Keep the device identity and signing keys together in a private directory.
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    client_path = directory / "client-id"
    private_path = directory / "private.key"
    public_path = directory / "public.key"
    token_path = directory / "token"
    identity_exists = [path.exists() for path in (client_path, private_path, public_path)]

    if not all(identity_exists) and (any(identity_exists) or token_path.exists()):
        raise AuthenticationError(
            "Plex authentication files are incomplete. Restore the plex authentication "
            "directory from backup, or remove it to pair again."
        )

    # Reuse the same client identity when verifying or refreshing saved credentials.
    client_id = client_path.read_text().strip() if all(identity_exists) else str(uuid4())
    if not client_id:
        raise AuthenticationError(
            "Plex client-id is empty; restore it or remove the auth directory."
        )

    login = MyPlexJWTLogin(
        session=session,
        oauth=True,
        headers={
            "X-Plex-Client-Identifier": client_id,
            "X-Plex-Product": "Watchlist Sync",
        },
        keypair=(str(private_path), str(public_path)) if all(identity_exists) else (None, None),
        jwtToken=token_path.read_text().strip() if token_path.exists() else None,
    )

    # Save new signing keys before pairing so the resulting token can be refreshed.
    if not all(identity_exists):
        login.generateKeypair(  # pyright: ignore[reportUnknownMemberType]
            keyfiles=(str(private_path), str(public_path))
        )
        client_path.write_text(client_id)

    return login


def _pair(login: MyPlexJWTLogin, stop: Event) -> None:
    # Display the short-lived authorization link, never the resulting token or keys.
    try:
        login.run()  # pyright: ignore[reportUnknownMemberType]
        url = login.oauthUrl()  # pyright: ignore[reportUnknownMemberType]
        logger.warning("Authorize Plex in your browser: %s", url)

        # Wake on shutdown rather than waiting for the whole pairing timeout.
        while not login.finished:
            if stop.wait(login.POLLINTERVAL):
                raise InterruptedError("Plex pairing cancelled")

        if stop.is_set():
            raise InterruptedError("Plex pairing cancelled")

        if not login.waitForLogin():
            raise AuthenticationError(
                "Plex pairing did not complete. Check connectivity and run the app again."
            )
    finally:
        login.stop()


def authenticate(config_dir: Path, session: Session, stop: Event) -> MyPlexAccount:
    """Authenticate with saved credentials, or wait for browser authorization."""
    directory = config_dir / "plex"
    login = _load_login(directory, session)

    # Pair a new device, or refresh an existing token when PlexAPI says it is due.
    if not login.jwtToken:  # pyright: ignore[reportUnknownMemberType]
        _pair(login, stop)
    elif not login.verifyJWT():
        login.refreshJWT()

    # Resolve the token to the account.
    token = login.jwtToken  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if not isinstance(token, str) or not token.strip():
        raise AuthenticationError(
            "Plex pairing did not complete. Check connectivity and run the app again."
        )

    # Verify the credential and account before replacing the saved token.
    if not token or not login.verifyJWT(refreshWithinDays=0):
        raise AuthenticationError(
            "Plex token verification failed; saved credentials were retained."
        )

    if stop.is_set():
        raise InterruptedError("Plex authentication cancelled")

    # Verify the token and store it atomically.
    account = MyPlexAccount(token=token, session=session)
    token_path = directory / "token"
    temporary_path = directory / "token.tmp"
    temporary_path.write_text(token)
    temporary_path.replace(token_path)

    return account


def with_authentication[T](
    settings: Settings, func: Callable[[MyPlexAccount], T], stop: Event
) -> T:
    """Run the given function with an authenticated Plex account."""
    with Session() as session:
        account = authenticate(settings.config_dir, session, stop)
        if stop.is_set():
            raise InterruptedError("Plex read cancelled")

        username: str = str(account.username or "<token>")  # pyright: ignore
        logger.info("Authenticated with Plex using account: %s", username)

        return func(account)
