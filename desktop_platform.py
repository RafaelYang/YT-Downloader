"""Small platform integrations used by the desktop launcher."""

from __future__ import annotations

import os
import json
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from desktop_config import BUNDLE_ID, PRODUCT_NAME, output_dir, user_data_dir


def launcher_arguments() -> list[str]:
    """Return the command that should be run after the user logs in."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--background"]
    return [sys.executable, str(Path(__file__).resolve().parent / "desktop_app.py"), "--background"]


def macos_launch_agent_path(launch_agents_dir: Path | None = None) -> Path:
    directory = launch_agents_dir or (Path.home() / "Library" / "LaunchAgents")
    return directory / f"{BUNDLE_ID}.plist"


def install_macos_autostart(
    launch_agents_dir: Path | None = None,
    program_arguments: Sequence[str] | None = None,
) -> Path:
    """Install a user LaunchAgent that starts the menu-bar app at login."""
    if sys.platform != "darwin" and launch_agents_dir is None:
        raise RuntimeError("macOS 自動啟動只能在 macOS 設定")

    path = macos_launch_agent_path(launch_agents_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": BUNDLE_ID,
        "ProgramArguments": list(program_arguments or launcher_arguments()),
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
    }
    with path.open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=True)
    path.chmod(0o600)
    return path


def remove_macos_autostart(launch_agents_dir: Path | None = None) -> bool:
    path = macos_launch_agent_path(launch_agents_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def macos_autostart_enabled(launch_agents_dir: Path | None = None) -> bool:
    return macos_launch_agent_path(launch_agents_dir).is_file()


def autostart_preference_path() -> Path:
    return user_data_dir() / "autostart.json"


def autostart_preference() -> bool | None:
    """Return None before the user/default choice has ever been persisted."""
    try:
        payload = json.loads(autostart_preference_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    enabled = payload.get("enabled")
    return enabled if isinstance(enabled, bool) else None


def set_autostart_preference(enabled: bool) -> None:
    path = autostart_preference_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"enabled": enabled}), encoding="utf-8")
    path.chmod(0o600)


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


def autostart_description() -> str:
    return f"登入後自動啟動 {PRODUCT_NAME}"
