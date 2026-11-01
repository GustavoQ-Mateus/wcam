import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_FOLDER = "wcam"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def default_data_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / APP_FOLDER
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base / APP_FOLDER


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WCAM_")

    console_port: int = 8080
    phone_port: int = 8443
    console_bind: str = "127.0.0.1"
    lan_ip: str | None = None
    data_dir: Path = Field(default_factory=default_data_dir)
    web_dist: Path = REPOSITORY_ROOT / "web" / "dist"
    locales_dir: Path = REPOSITORY_ROOT / "locales"
    extra_allowed_hosts: list[str] = Field(default_factory=list[str])
    virtual_camera: Literal["auto", "obs", "fake"] = "auto"
    quality_reference: Path | None = None
