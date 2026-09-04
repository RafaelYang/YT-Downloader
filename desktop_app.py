"""Desktop launcher for YT Downloader by 學人新創."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import secrets
import signal
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import IO, Any
from urllib.parse import urlencode

from desktop_config import (
    APP_VERSION,
    DEFAULT_PORT,
    PRODUCT_NAME,
    ensure_desktop_directories,
    resource_dir,
    user_data_dir,
)
from desktop_platform import (
    autostart_preference,
    install_macos_autostart,
    macos_autostart_enabled,
    open_output_folder,
    remove_macos_autostart,
    set_autostart_preference,
)


class InstanceLock:
    """A per-user non-blocking process lock that works on macOS and Windows."""

    def __init__(self, path: Path):
        self.path = path
        self.handle: IO[str] | None = None

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+")
        try:
            if sys.platform.startswith("win"):
                import msvcrt

                handle.seek(0)
                if handle.read(1) == "":
                    handle.write("0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            handle.close()
            return False
        self.handle = handle
        return True

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            if sys.platform.startswith("win"):
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def runtime_file() -> Path:
    return user_data_dir() / "runtime.json"


def write_runtime_state(port: int, token: str) -> None:
    path = runtime_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "product": PRODUCT_NAME,
                "version": APP_VERSION,
                "pid": os.getpid(),
                "port": port,
                "token": token,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    path.chmod(0o600)


def read_runtime_state() -> dict[str, Any] | None:
    try:
        value = json.loads(runtime_file().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    if value.get("product") != PRODUCT_NAME:
        return None
    if not isinstance(value.get("port"), int) or not isinstance(value.get("token"), str):
        return None
    return value


def health_url(port: int) -> str:
    return f"http://127.0.0.1:{port}/api/health"


def launch_url(port: int, token: str) -> str:
    return f"http://127.0.0.1:{port}/launch?{urlencode({'token': token})}"


def is_healthy(port: int, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(health_url(port), timeout=timeout) as response:
            payload = json.load(response)
        return payload.get("status") == "ok" and payload.get("product") == PRODUCT_NAME
    except (OSError, ValueError, urllib.error.URLError):
        return False


def pot_provider_resources() -> tuple[Path, Path] | None:
    """Locate the bundled Node runtime and loopback PO-token provider server."""
    resources = resource_dir()
    node_candidates = [
        resources / "tools" / "node",
        resources / "vendor" / "macos-arm64" / "node",
    ]
    node_path = next(
        (path for path in node_candidates if path.is_file() and os.access(path, os.X_OK)),
        None,
    )
    if node_path is None:
        system_node = shutil.which("node")
        node_path = Path(system_node) if system_node else None

    server_candidates = [
        resources / "pot-provider" / "server" / "build" / "main.js",
        resources
        / "vendor"
        / "bgutil-ytdlp-pot-provider"
        / "server"
        / "build"
        / "main.js",
    ]
    server_path = next((path for path in server_candidates if path.is_file()), None)
    if node_path is None or server_path is None:
        return None
    return node_path, server_path


def reserve_loopback_port() -> int:
    """Ask the OS for a currently available IPv4 loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_pot_provider(
    process: subprocess.Popen,
    url: str,
    timeout: float = 30.0,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with urllib.request.urlopen(f"{url}/ping", timeout=1.0) as response:
                payload = json.load(response)
            if payload.get("version"):
                return True
        except (OSError, ValueError, urllib.error.URLError):
            time.sleep(0.2)
    return False


def stop_pot_provider(process: subprocess.Popen | None) -> None:
    """Stop only the provider process created by this desktop instance."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def start_pot_provider() -> tuple[subprocess.Popen, str] | None:
    """Start the bundled provider on a random loopback port."""
    resources = pot_provider_resources()
    if resources is None:
        print("⚠️ 找不到高畫質相容元件，將只顯示可直接取得的畫質。")
        return None

    node_path, server_path = resources
    port = reserve_loopback_port()
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [str(node_path), str(server_path), "--port", str(port)],
        cwd=server_path.parent.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if wait_for_pot_provider(process, url):
        return process, url

    stop_pot_provider(process)
    print("⚠️ 高畫質相容元件啟動失敗，將只顯示可直接取得的畫質。")
    return None


def open_existing_instance(wait_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        state = read_runtime_state()
        if state and is_healthy(state["port"]):
            webbrowser.open(launch_url(state["port"], state["token"]))
            return True
        time.sleep(0.15)
    return False


def create_macos_reopen_delegate(on_reopen):
    """Create an NSApplication delegate that opens the UI when Finder reopens the app."""
    if sys.platform != "darwin":
        return None

    import Foundation

    class ReopenDelegate(Foundation.NSObject):
        def applicationShouldHandleReopen_hasVisibleWindows_(
            self, _application: Any, _has_visible_windows: bool
        ) -> bool:
            self.on_reopen()
            return True

    delegate = ReopenDelegate.alloc().init()
    delegate.on_reopen = on_reopen
    return delegate


def wait_for_server(port: int, server_thread: threading.Thread, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and server_thread.is_alive():
        if is_healthy(port):
            return True
        time.sleep(0.1)
    return False


def run_tray(server: Any, port: int, token: str) -> None:
    """Run the native tray/menu-bar loop on the main thread."""
    import pystray
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), (92, 69, 220, 255))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, 61, 61), radius=14, fill=(92, 69, 220, 255))
    draw.polygon(((25, 17), (25, 47), (49, 32)), fill=(255, 255, 255, 255))

    def on_open(_icon: Any = None, _item: Any = None) -> None:
        webbrowser.open(launch_url(port, token))

    def on_autostart(_icon: Any, _item: Any) -> None:
        if sys.platform == "darwin":
            if macos_autostart_enabled():
                remove_macos_autostart()
                set_autostart_preference(False)
            else:
                install_macos_autostart()
                set_autostart_preference(True)

    def on_quit(icon: Any, _item: Any) -> None:
        server.should_exit = True
        icon.stop()

    nsapplication = None
    reopen_delegate = None
    if sys.platform == "darwin":
        import AppKit

        nsapplication = AppKit.NSApplication.sharedApplication()
        reopen_delegate = create_macos_reopen_delegate(on_open)
        nsapplication.setDelegate_(reopen_delegate)

    menu = pystray.Menu(
        pystray.MenuItem("開啟 YT Downloader", on_open, default=True),
        pystray.MenuItem("開啟下載資料夾", lambda _icon, _item: open_output_folder()),
        pystray.MenuItem(
            "登入後自動啟動",
            on_autostart,
            checked=lambda _item: sys.platform == "darwin" and macos_autostart_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("結束", on_quit),
    )
    icon_options = (
        {"darwin_nsapplication": nsapplication}
        if nsapplication is not None
        else {}
    )
    icon = pystray.Icon(
        "yt_downloader_xueren",
        image,
        PRODUCT_NAME,
        menu,
        **icon_options,
    )
    try:
        icon.run()
    finally:
        if (
            nsapplication is not None
            and reopen_delegate is not None
            and nsapplication.delegate() is reopen_delegate
        ):
            nsapplication.setDelegate_(None)


def wait_without_tray(server: Any) -> None:
    stop = threading.Event()

    def request_stop(_signum: int, _frame: Any) -> None:
        server.should_exit = True
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    while not server.should_exit and not stop.wait(0.5):
        pass


def configure_autostart(enable: bool) -> int:
    if sys.platform != "darwin":
        print("目前這個預覽版只實作 macOS 自動啟動設定。")
        return 2
    if enable:
        print(f"已設定登入後自動啟動：{install_macos_autostart()}")
        set_autostart_preference(True)
    else:
        removed = remove_macos_autostart()
        set_autostart_preference(False)
        print("已移除登入自動啟動。" if removed else "尚未設定登入自動啟動。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=PRODUCT_NAME)
    parser.add_argument("--background", action="store_true", help="啟動後不要自動開啟瀏覽器")
    parser.add_argument("--no-tray", action="store_true", help="停用選單列圖示（測試用）")
    parser.add_argument("--no-autostart", action="store_true", help="不要在封裝版首次啟動時設定自動啟動")
    parser.add_argument("--install-autostart", action="store_true", help="設定登入後自動啟動")
    parser.add_argument("--remove-autostart", action="store_true", help="移除登入自動啟動")
    parser.add_argument("--status", action="store_true", help="顯示背景服務狀態")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.install_autostart:
        return configure_autostart(True)
    if args.remove_autostart:
        return configure_autostart(False)
    if args.status:
        state = read_runtime_state()
        running = bool(state and is_healthy(state["port"]))
        print("執行中" if running else "未執行")
        return 0 if running else 1
    if not 1024 <= args.port <= 65535:
        print("連接埠必須介於 1024 到 65535。", file=sys.stderr)
        return 2

    paths = ensure_desktop_directories()
    lock = InstanceLock(paths["data"] / "runtime.lock")
    if not lock.acquire():
        if open_existing_instance():
            return 0
        print("背景程式已存在，但目前無法連線。請先從選單列結束後再試。", file=sys.stderr)
        return 1

    server = None
    thread = None
    pot_process = None
    try:
        token = secrets.token_urlsafe(32)
        os.environ["YT_DESKTOP"] = "1"
        os.environ["YT_LOCAL_TOKEN"] = token

        pot_runtime = start_pot_provider()
        if pot_runtime is not None:
            pot_process, pot_url = pot_runtime
            os.environ["YT_POT_PROVIDER_URL"] = pot_url

        import uvicorn
        from app import app

        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=args.port, log_level="warning")
        )
        thread = threading.Thread(target=server.run, name="local-api", daemon=True)
        write_runtime_state(args.port, token)
        thread.start()

        if not wait_for_server(args.port, thread):
            print("本機服務啟動失敗。", file=sys.stderr)
            return 1

        if getattr(sys, "frozen", False) and sys.platform == "darwin" and not args.no_autostart:
            preference = autostart_preference()
            if preference is not False:
                # Rewriting also repairs the executable path if the App was moved.
                install_macos_autostart()
                if preference is None:
                    set_autostart_preference(True)

        if not args.background:
            webbrowser.open(launch_url(args.port, token))

        if args.no_tray:
            wait_without_tray(server)
        else:
            try:
                run_tray(server, args.port, token)
            except ImportError:
                wait_without_tray(server)

        server.should_exit = True
        thread.join(timeout=10)
        return 0
    finally:
        if server is not None:
            server.should_exit = True
        if runtime_file().exists():
            try:
                runtime_file().unlink()
            except OSError:
                pass
        stop_pot_provider(pot_process)
        lock.release()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
