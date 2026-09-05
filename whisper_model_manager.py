"""Securely provision the Whisper model used by the desktop application."""

from __future__ import annotations

import hashlib
import shutil
import ssl
import subprocess
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_hash_from_url(url: str) -> str:
    """Extract Whisper's published SHA-256 directory component from its URL."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Whisper 模型只允許從 HTTPS 下載")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or len(parts[-2]) != 64:
        raise ValueError("Whisper 模型網址缺少 SHA-256 驗證值")
    expected = parts[-2].lower()
    if any(character not in "0123456789abcdef" for character in expected):
        raise ValueError("Whisper 模型 SHA-256 格式不正確")
    return expected


def is_verified_model(path: Path, expected_sha256: str) -> bool:
    """Return whether a model exists and matches the publisher-provided digest."""
    return path.is_file() and sha256_file(path) == expected_sha256


def _python_https_download(url: str, destination: Path) -> None:
    """Fallback HTTPS download using an explicit certificate bundle."""
    try:
        import certifi

        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()

    with urllib.request.urlopen(url, context=context, timeout=60) as response:
        with destination.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)


def download_verified_model(
    url: str,
    destination: Path,
    expected_sha256: str,
    curl_path: Path | None = None,
    model_label: str = "Whisper 模型",
) -> Path:
    """Download with certificate verification, then atomically install the model."""
    if curl_path is None:
        discovered_curl = shutil.which("curl.exe") or shutil.which("curl")
        curl_path = Path(discovered_curl) if discovered_curl else Path("/usr/bin/curl")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}.download"
    )
    try:
        if curl_path.is_file():
            completed = subprocess.run(
                [
                    str(curl_path),
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--proto",
                    "=https",
                    "--tlsv1.2",
                    "--output",
                    str(temporary),
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or f"curl 結束碼 {completed.returncode}"
                raise RuntimeError(detail)
        else:
            _python_https_download(url, temporary)

        if not is_verified_model(temporary, expected_sha256):
            raise RuntimeError("下載完成但 SHA-256 驗證失敗")
        temporary.replace(destination)
        return destination
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"{model_label}下載失敗：{exc}") from exc


def ensure_whisper_model(
    model_name: str,
    model_url: str,
    model_directory: Path,
    legacy_cache_directory: Path | None = None,
) -> Path:
    """Reuse a verified model cache or securely download a fresh model."""
    expected_sha256 = expected_hash_from_url(model_url)
    model_filename = Path(urlparse(model_url).path).name
    if not model_filename:
        raise ValueError("Whisper 模型網址缺少檔名")
    destination = model_directory / model_filename
    verified = find_verified_whisper_model(
        model_name,
        model_url,
        model_directory,
        legacy_cache_directory,
    )
    if verified == destination:
        return destination

    legacy = verified
    if legacy is not None:
        model_directory.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}.copy"
        )
        try:
            shutil.copy2(legacy, temporary)
            if not is_verified_model(temporary, expected_sha256):
                raise RuntimeError("既有 Whisper 模型複製後驗證失敗")
            temporary.replace(destination)
            return destination
        finally:
            temporary.unlink(missing_ok=True)

    return download_verified_model(
        model_url,
        destination,
        expected_sha256,
    )


def find_verified_whisper_model(
    model_name: str,
    model_url: str,
    model_directory: Path,
    legacy_cache_directory: Path | None = None,
) -> Path | None:
    """Find a verified current or legacy cache without downloading anything."""
    expected_sha256 = expected_hash_from_url(model_url)
    model_filename = Path(urlparse(model_url).path).name
    if not model_filename:
        raise ValueError("Whisper 模型網址缺少檔名")

    destination = model_directory / model_filename
    legacy_cache_directory = (
        Path.home() / ".cache" / "whisper"
        if legacy_cache_directory is None
        else legacy_cache_directory
    )
    candidates = [
        destination,
        legacy_cache_directory / model_filename,
        legacy_cache_directory / f"{model_name}.pt",
    ]
    return next(
        (path for path in candidates if is_verified_model(path, expected_sha256)),
        None,
    )
