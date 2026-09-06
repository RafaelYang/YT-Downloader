"""Shared desktop configuration and platform-specific filesystem paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Mapping


PRODUCT_NAME = "YT Downloader by 學人新創"
PRODUCT_SLUG = "YT Downloader"
PUBLISHER_NAME = "學人新創"
APP_VERSION = "0.1.5-dev"
BUNDLE_ID = "tw.xueren.yt-downloader"
DEFAULT_PORT = 18765


def resource_dir() -> Path:
    """Return the source/bundle directory that contains static assets."""
    frozen_dir = getattr(sys, "_MEIPASS", None)
    if frozen_dir:
        return Path(frozen_dir)
    return Path(__file__).resolve().parent


def user_data_dir(
    platform_name: str | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the per-user writable application data directory."""
    env = os.environ if environ is None else environ
    explicit = env.get("YT_DATA_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()

    platform_name = sys.platform if platform_name is None else platform_name
    home = Path.home() if home is None else home

    if platform_name == "darwin":
        return home / "Library" / "Application Support" / PUBLISHER_NAME / PRODUCT_SLUG
    if platform_name.startswith("win"):
        local_app_data = env.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / PUBLISHER_NAME / PRODUCT_SLUG
        return home / "AppData" / "Local" / PUBLISHER_NAME / PRODUCT_SLUG
    return home / ".local" / "share" / PUBLISHER_NAME / PRODUCT_SLUG


def output_dir(
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the default folder for completed user files."""
    env = os.environ if environ is None else environ
    explicit = env.get("YT_OUTPUT_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    home = Path.home() if home is None else home
    return home / "Downloads"


def model_dir(
    data: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Return the model directory, allowing an explicit test/developer override."""
    env = os.environ if environ is None else environ
    explicit = env.get("YT_MODEL_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    data = user_data_dir(environ=env) if data is None else data
    return data / "models"


def ensure_desktop_directories() -> dict[str, Path]:
    """Create and return writable desktop runtime directories."""
    data = user_data_dir()
    paths = {
        "data": data,
        "jobs": data / "jobs",
        "logs": data / "logs",
        "models": model_dir(data),
        "updates": data / "updates",
        "output": output_dir(),
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths
