"""Runtime configuration read from environment variables."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(hide_input_in_errors=True)

    config_dir: Path = Path("/config")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    sync_interval_seconds: float = Field(default=30, ge=1, allow_inf_nan=False)
