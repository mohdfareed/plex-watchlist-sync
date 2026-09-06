"""Runtime configuration, validation, and initialization."""

import logging
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    config_dir: Path = Path("/config")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    sync_interval_seconds: float = Field(default=30, ge=1, allow_inf_nan=False)


def load_settings(logger: logging.Logger) -> Settings:
    """Load settings from environment variables and validate them."""

    # Start logging before validation so configuration failures are visible.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )

    try:
        settings = Settings()
    except ValidationError as error:
        # Report validation errors without including their supplied values.
        for issue in error.errors(include_input=False, include_context=False, include_url=False):
            field = ".".join(str(part) for part in issue["loc"]).upper()
            logger.error("%s: %s", field, issue["msg"])
        raise

    # Configure our verbosity without exposing library HTTP/auth diagnostics.
    logger.setLevel(settings.log_level)
    logging.getLogger("plexapi").disabled = True
    logging.getLogger("requests").setLevel(logging.CRITICAL)
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)

    return settings
