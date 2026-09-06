"""Securely provision the pinned offline multilingual translation model."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from whisper_model_manager import download_verified_model, is_verified_model


MODEL_ID = "facebook/m2m100_418M"
MODEL_REVISION = "55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636"
MODEL_DIRECTORY_NAME = f"m2m100-418m-{MODEL_REVISION[:8]}"
MODEL_DOWNLOAD_SIZE_BYTES = 1_941_931_012
MODEL_FILES = {
    "config.json": "df0ae43e4e4b0d7e3c97b7f447857a70ef6b6a2aa1f145cedbcc730d95f67134",
    "generation_config.json": "aed76366507333ddbb8bd49960f23c82fe6446b3319a46a54befdb45324ccf61",
    "pytorch_model.bin": "d907ea45e4e4b9db163382a6674f6218b3c59566fe06d77f4055c208b4e87ed1",
    "sentencepiece.bpe.model": "d8f7c76ed2a5e0822be39f0a4f95a55eb19c78f4593ce609e2edbc2aea4d380a",
    "special_tokens_map.json": "c1a4f86c3874d279ae1b2a05162858db5dd6c61665d84223ed886cbcff08fda6",
    "tokenizer_config.json": "a53e6aa83da0b82565ed90c3849056307a9453843322ac5b8439ec4b9497fe48",
    "vocab.json": "b6e77e474aeea8f441363aca7614317c06381f3eacfe10fb9856d5081d1074cc",
}


def is_verified_translation_model(path: Path) -> bool:
    """Return whether every pinned file is present with its expected digest."""
    return path.is_dir() and all(
        is_verified_model(path / filename, digest)
        for filename, digest in MODEL_FILES.items()
    )


def ensure_translation_model(model_directory: Path) -> Path:
    """Download and atomically install the pinned translation model."""
    destination = model_directory / MODEL_DIRECTORY_NAME
    if is_verified_translation_model(destination):
        return destination

    model_directory.mkdir(parents=True, exist_ok=True)
    temporary = model_directory / f".{MODEL_DIRECTORY_NAME}.{uuid.uuid4().hex}.download"
    temporary.mkdir()
    try:
        for filename, digest in MODEL_FILES.items():
            url = (
                f"https://huggingface.co/{MODEL_ID}/resolve/"
                f"{MODEL_REVISION}/{filename}?download=true"
            )
            download_verified_model(
                url,
                temporary / filename,
                digest,
                model_label="多語轉繁中翻譯模型",
            )

        if not is_verified_translation_model(temporary):
            raise RuntimeError("多語轉繁中翻譯模型檔案不完整")
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
