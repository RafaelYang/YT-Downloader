"""Small platform integrations used by the desktop launcher."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from desktop_config import BUNDLE_ID, PRODUCT_NAME, output_dir, user_data_dir


WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WINDOWS_RUN_VALUE_NAME = PRODUCT_NAME


def macos_launch_agent_path(launch_agents_dir: Path | None = None) -> Path:
    directory = launch_agents_dir or (Path.home() / "Library" / "LaunchAgents")
    return directory / f"{BUNDLE_ID}.plist"


def remove_macos_autostart(launch_agents_dir: Path | None = None) -> bool:
    path = macos_launch_agent_path(launch_agents_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def _windows_registry(registry: Any | None = None) -> Any:
    if registry is not None:
        return registry
    if not sys.platform.startswith("win"):
        raise RuntimeError("Windows 自動啟動只能在 Windows 設定")
    import winreg

    return winreg


def remove_windows_autostart(registry: Any | None = None) -> bool:
    """Remove the per-user Windows Run entry if it exists."""
    winreg = _windows_registry(registry)
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            WINDOWS_RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, WINDOWS_RUN_VALUE_NAME)
    except FileNotFoundError:
        return False
    return True


def autostart_preference_path() -> Path:
    return user_data_dir() / "autostart.json"


def remove_autostart_preference() -> bool:
    """Remove the retired login-startup preference if it exists."""
    path = autostart_preference_path()
    if not path.exists():
        return False
    path.unlink()
    return True


def remove_legacy_autostart() -> bool:
    """Remove login-startup state left by desktop previews before 0.1.1-dev."""
    if sys.platform == "darwin":
        removed = remove_macos_autostart()
    elif sys.platform.startswith("win"):
        removed = remove_windows_autostart()
    else:
        return False
    return remove_autostart_preference() or removed


def open_output_folder() -> None:
    folder = output_dir()
    folder.mkdir(parents=True, exist_ok=True)
    open_folder(folder)


def open_folder(folder: Path) -> None:
    """Open an existing folder using the platform file manager."""
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"資料夾不存在：{folder}")

    if sys.platform == "darwin":
        subprocess.Popen(
            ["/usr/bin/open", str(folder)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif sys.platform.startswith("win"):
        os.startfile(str(folder))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(
            ["xdg-open", str(folder)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
