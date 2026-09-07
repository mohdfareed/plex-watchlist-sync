"""Authenticated HTTP transport for Scryer's read queries."""

from types import TracebackType
from typing import Self

from pydantic import BaseModel, SecretStr, ValidationError
from requests import RequestException, Session


class ScryerError(Exception):
    """A safe diagnostic message without remote bodies, URLs, or credentials."""


class ScryerClient:
    def __init__(self, graphql_url: str, api_key: SecretStr) -> None:
        self._url = graphql_url
        self._api_key = api_key
        self._session = Session()
        # Use only the configured API key, not implicit netrc credentials.
        self._session.trust_env = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._session.close()

    def _query[T: BaseModel](self, query: str, variables: dict[str, int], model: type[T]) -> T:
        # Bound requests and reject redirects so credentials stay at the configured endpoint.
        try:
            with self._session.post(
                self._url,
                json={"query": query, "variables": variables},
                headers={"Authorization": f"Bearer {self._api_key.get_secret_value()}"},
                timeout=(10, 30),
                allow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise ScryerError(
                        f"Scryer HTTP request failed (status {response.status_code})."
                    )
                payload = response.json()
        except RequestException:
            raise ScryerError(
                "Scryer HTTP request failed; check connectivity and the API key."
            ) from None
        except ValueError:
            raise ScryerError("Scryer returned invalid JSON.") from None

        # Never accept partial GraphQL data as a complete diagnostic read.
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise ScryerError("Scryer returned no GraphQL data; check the endpoint and API key.")
        if payload.get("errors"):
            raise ScryerError("Scryer query failed; check permissions and API version.")

        try:
            return model.model_validate(payload["data"])
        except ValidationError:
            raise ScryerError("Scryer response does not match the expected schema.") from None
