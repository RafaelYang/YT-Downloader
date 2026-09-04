import json
import plistlib
import sys
from pathlib import Path

from desktop_app import (
    InstanceLock,
    create_macos_reopen_delegate,
    health_url,
    launch_url,
    pot_provider_resources,
    reserve_loopback_port,
)
import desktop_app
from desktop_config import model_dir, output_dir, user_data_dir
import desktop_platform
from desktop_platform import install_macos_autostart, macos_launch_agent_path, open_folder
from desktop_platform import (
    install_windows_autostart,
    remove_windows_autostart,
    windows_autostart_command,
    windows_autostart_enabled,
)


class FakeWindowsRegistry:
    HKEY_CURRENT_USER = object()
    KEY_SET_VALUE = 1
    KEY_READ = 2
    REG_SZ = 1

    class Key:
        def __init__(self, registry):
            self.registry = registry

        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _traceback):
            return False

    def __init__(self):
        self.values = {}

    def CreateKeyEx(self, _root, _path, _reserved, _access):
        return self.Key(self)

    def OpenKey(self, _root, _path, _reserved, _access):
        if not self.values:
            raise FileNotFoundError
        return self.Key(self)

    def SetValueEx(self, _key, name, _reserved, value_type, value):
        self.values[name] = (value, value_type)

    def QueryValueEx(self, _key, name):
        if name not in self.values:
            raise FileNotFoundError
        return self.values[name]

    def DeleteValue(self, _key, name):
        if name not in self.values:
            raise FileNotFoundError
        del self.values[name]


def test_platform_data_paths():
    home = Path("/Users/tester")
    assert user_data_dir("darwin", home, {}) == (
        home / "Library" / "Application Support" / "學人新創" / "YT Downloader"
    )
    assert user_data_dir("win32", home, {"LOCALAPPDATA": "C:/Local"}) == (
        Path("C:/Local") / "學人新創" / "YT Downloader"
    )
    assert output_dir(home, {}) == home / "Downloads"


def test_explicit_data_path_override(tmp_path):
    assert user_data_dir(environ={"YT_DATA_DIR": str(tmp_path)}) == tmp_path.resolve()
    assert model_dir(environ={"YT_MODEL_DIR": str(tmp_path)}) == tmp_path.resolve()


def test_instance_lock_allows_only_one_owner(tmp_path):
    first = InstanceLock(tmp_path / "runtime.lock")
    second = InstanceLock(tmp_path / "runtime.lock")
    assert first.acquire()
    assert not second.acquire()
    first.release()
    assert second.acquire()
    second.release()


def test_macos_launch_agent_contents(tmp_path):
    arguments = ["/Applications/YT Downloader.app/Contents/MacOS/desktop_app", "--background"]
    path = install_macos_autostart(tmp_path, arguments)
    assert path == macos_launch_agent_path(tmp_path)
    with path.open("rb") as handle:
        payload = plistlib.load(handle)
    assert payload["ProgramArguments"] == arguments
    assert payload["RunAtLoad"] is True
    if sys.platform == "darwin":
        assert path.stat().st_mode & 0o777 == 0o600


def test_autostart_preference_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(desktop_platform, "autostart_preference_path", lambda: tmp_path / "pref.json")
    assert desktop_platform.autostart_preference() is None
    desktop_platform.set_autostart_preference(False)
    assert desktop_platform.autostart_preference() is False
    desktop_platform.set_autostart_preference(True)
    assert desktop_platform.autostart_preference() is True


def test_windows_autostart_round_trip_uses_current_user_registry():
    registry = FakeWindowsRegistry()
    command = windows_autostart_command(
        [r"C:\Program Files\YT Downloader\YT Downloader.exe", "--background"]
    )

    assert command == '"C:\\Program Files\\YT Downloader\\YT Downloader.exe" --background'
    assert not windows_autostart_enabled(registry)
    assert install_windows_autostart(registry, command) == command
    assert windows_autostart_enabled(registry)
    assert remove_windows_autostart(registry)
    assert not windows_autostart_enabled(registry)
    assert not remove_windows_autostart(registry)


def test_local_urls_do_not_expose_token_in_health_endpoint():
    assert health_url(18765) == "http://127.0.0.1:18765/api/health"
    url = launch_url(18765, "secret value")
    assert url.startswith("http://127.0.0.1:18765/launch?")
    assert "secret+value" in url


def test_macos_reopen_delegate_invokes_open_callback():
    if sys.platform != "darwin":
        return

    calls = []
    delegate = create_macos_reopen_delegate(lambda: calls.append("opened"))

    assert delegate.applicationShouldHandleReopen_hasVisibleWindows_(None, False) is True
    assert calls == ["opened"]


def test_open_folder_uses_macos_finder(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(desktop_platform.sys, "platform", "darwin")
    monkeypatch.setattr(
        desktop_platform.subprocess,
        "Popen",
        lambda args, **kwargs: calls.append((args, kwargs)),
    )

    open_folder(tmp_path)

    assert calls[0][0] == ["/usr/bin/open", str(tmp_path.resolve())]
    assert calls[0][1]["stdout"] is desktop_platform.subprocess.DEVNULL
    assert calls[0][1]["stderr"] is desktop_platform.subprocess.DEVNULL


def test_pot_provider_resources_prefer_bundled_runtime(tmp_path, monkeypatch):
    node = tmp_path / "tools" / "node"
    server = tmp_path / "pot-provider" / "server" / "build" / "main.js"
    node.parent.mkdir(parents=True)
    server.parent.mkdir(parents=True)
    node.write_text("node", encoding="utf-8")
    server.write_text("server", encoding="utf-8")
    node.chmod(0o755)
    monkeypatch.setattr(desktop_app, "resource_dir", lambda: tmp_path)

    assert pot_provider_resources() == (node, server)


def test_pot_provider_resources_accept_windows_node_exe(tmp_path, monkeypatch):
    node = tmp_path / "tools" / "node.exe"
    server = tmp_path / "pot-provider" / "server" / "build" / "main.js"
    node.parent.mkdir(parents=True)
    server.parent.mkdir(parents=True)
    node.write_text("node", encoding="utf-8")
    server.write_text("server", encoding="utf-8")
    node.chmod(0o755)
    monkeypatch.setattr(desktop_app, "resource_dir", lambda: tmp_path)

    assert pot_provider_resources() == (node, server)


def test_reserved_provider_port_is_loopback_connectable():
    port = reserve_loopback_port()
    assert 1024 <= port <= 65535
