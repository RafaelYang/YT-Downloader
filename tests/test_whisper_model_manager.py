import hashlib
from pathlib import Path

import pytest

import whisper_model_manager as manager


def model_url_for(content: bytes) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    return f"https://models.example.test/{digest}/small.pt", digest


def test_expected_hash_requires_https_and_valid_digest():
    url, digest = model_url_for(b"model")
    assert manager.expected_hash_from_url(url) == digest

    with pytest.raises(ValueError):
        manager.expected_hash_from_url(url.replace("https://", "http://"))


def test_ensure_whisper_model_copies_only_verified_legacy_cache(tmp_path):
    content = b"verified whisper model"
    url, digest = model_url_for(content)
    legacy = tmp_path / "legacy"
    destination = tmp_path / "app-models"
    legacy.mkdir()
    (legacy / "small.pt").write_bytes(content)

    result = manager.ensure_whisper_model("small", url, destination, legacy)

    assert result == destination / "small.pt"
    assert result.read_bytes() == content
    assert manager.sha256_file(result) == digest


def test_download_verified_model_rejects_bad_content(tmp_path, monkeypatch):
    expected_content = b"expected"
    url, digest = model_url_for(expected_content)
    fake_curl = tmp_path / "curl"
    fake_curl.write_text("placeholder", encoding="utf-8")

    def fake_run(command, **kwargs):
        output_path = Path(command[command.index("--output") + 1])
        output_path.write_bytes(b"tampered")

        class Completed:
            returncode = 0
            stderr = ""

        return Completed()

    monkeypatch.setattr(manager.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="SHA-256"):
        manager.download_verified_model(
            url,
            tmp_path / "small.pt",
            digest,
            curl_path=fake_curl,
        )
    assert not (tmp_path / "small.pt").exists()
