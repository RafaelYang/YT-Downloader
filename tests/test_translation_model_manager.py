import hashlib
from pathlib import Path

import translation_model_manager as manager


def test_translation_model_is_installed_only_after_every_hash_is_verified(
    tmp_path,
    monkeypatch,
):
    fake_contents = {
        filename: f"verified:{filename}".encode()
        for filename in manager.MODEL_FILES
    }
    monkeypatch.setattr(
        manager,
        "MODEL_FILES",
        {
            filename: hashlib.sha256(content).hexdigest()
            for filename, content in fake_contents.items()
        },
    )

    def fake_download(url, destination, digest, **kwargs):
        filename = Path(destination).name
        Path(destination).write_bytes(fake_contents[filename])
        return Path(destination)

    monkeypatch.setattr(manager, "download_verified_model", fake_download)

    result = manager.ensure_translation_model(tmp_path)

    assert result == tmp_path / manager.MODEL_DIRECTORY_NAME
    assert manager.is_verified_translation_model(result)
    assert not list(tmp_path.glob(".*.download"))
