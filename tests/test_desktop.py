import json
import sys
from pathlib import Path

from desktop_app import (
    InstanceLock,
    configure_frozen_stdio,
    check_ai_runtime_cli,
    create_macos_reopen_delegate,
    health_url,
    launch_url,
    load_tray_image,
    pot_provider_resources,
    remove_legacy_autostart_cli,
    reserve_loopback_port,
)
import desktop_app
from desktop_config import model_dir, output_dir, user_data_dir
import desktop_platform
from desktop_platform import macos_launch_agent_path, open_folder, remove_legacy_autostart
from desktop_platform import (
    remove_windows_autostart,
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


def test_remove_windows_legacy_autostart_uses_current_user_registry():
    registry = FakeWindowsRegistry()
    registry.values[desktop_platform.WINDOWS_RUN_VALUE_NAME] = (
        '"C:\\Program Files\\YT Downloader\\YT Downloader.exe" --background',
        registry.REG_SZ,
    )
    assert remove_windows_autostart(registry)
    assert registry.values == {}
    assert not remove_windows_autostart(registry)


def test_remove_macos_legacy_autostart_and_preference(tmp_path, monkeypatch):
    launch_agents = tmp_path / "LaunchAgents"
    launch_agent = macos_launch_agent_path(launch_agents)
    launch_agent.parent.mkdir(parents=True)
    launch_agent.write_text("legacy", encoding="utf-8")
    preference = tmp_path / "autostart.json"
    preference.write_text('{"enabled": true}', encoding="utf-8")

    monkeypatch.setattr(desktop_platform.sys, "platform", "darwin")
    monkeypatch.setattr(
        desktop_platform,
        "macos_launch_agent_path",
        lambda launch_agents_dir=None: launch_agent,
    )
    monkeypatch.setattr(desktop_platform, "autostart_preference_path", lambda: preference)

    assert remove_legacy_autostart()
    assert not launch_agent.exists()
    assert not preference.exists()
    assert not remove_legacy_autostart()


def test_remove_legacy_autostart_cli_rejects_unsupported_platform(monkeypatch):
    monkeypatch.setattr(desktop_app.sys, "platform", "linux")
    assert remove_legacy_autostart_cli() == 2


def test_ai_runtime_check_loads_translation_and_traditional_chinese_dependencies():
    assert check_ai_runtime_cli() == 0


def test_local_urls_do_not_expose_token_in_health_endpoint():
    assert health_url(18765) == "http://127.0.0.1:18765/api/health"
    url = launch_url(18765, "secret value")
    assert url.startswith("http://127.0.0.1:18765/launch?")
    assert "secret+value" in url


def test_frozen_stdio_writes_startup_log(tmp_path, monkeypatch):
    original_stdout = desktop_app.sys.stdout
    original_stderr = desktop_app.sys.stderr
    monkeypatch.setattr(desktop_app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(desktop_app, "user_data_dir", lambda: tmp_path)

    stream = configure_frozen_stdio()
    try:
        assert stream is not None
        print("startup diagnostic")
        stream.flush()
    finally:
        desktop_app.sys.stdout = original_stdout
        desktop_app.sys.stderr = original_stderr
        if stream is not None:
            stream.close()

    log = (tmp_path / "logs" / "desktop.log").read_text(encoding="utf-8")
    assert "YT Downloader by 學人新創" in log
    assert "startup diagnostic" in log


def test_tray_image_loads_branded_asset(tmp_path, monkeypatch):
    from PIL import Image

    Image.new("RGBA", (128, 128), (255, 82, 113, 255)).save(
        tmp_path / "app-icon.png"
    )
    monkeypatch.setattr(desktop_app, "resource_dir", lambda: tmp_path)

    image = load_tray_image()

    assert image.size == (64, 64)
    assert image.getpixel((32, 32)) == (255, 82, 113, 255)


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
