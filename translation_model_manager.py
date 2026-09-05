"""Securely provision the pinned offline English-to-Chinese model."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from whisper_model_manager import download_verified_model, is_verified_model


MODEL_ID = "Helsinki-NLP/opus-mt-en-zh"
MODEL_REVISION = "408d9bc410a388e1d9aef112a2daba955b945255"
MODEL_DIRECTORY_NAME = f"opus-mt-en-zh-{MODEL_REVISION[:8]}"
MODEL_DOWNLOAD_SIZE_BYTES = 315_317_575
MODEL_FILES = {
    "config.json": "bcae8ed74fed77fb51c58462b62397fee6b1a1a34aece79183a0dd02ad329e71",
    "generation_config.json": "837839ed0534a27084f9b980fc33f47729052dd89cb26cca7ac830765ed30e49",
    "pytorch_model.bin": "69a1d6ec829cee349360b3b677ac0aa99a7d88822d1a6578370029efffdca3f5",
    "source.spm": "5775ddc9e3ff2fae91554da56468ad35ff56edaba870fea74447bc7234bfdaa8",
    "target.spm": "81dc94efa84e4025ef38d25d5d07429fe41e3eb29d44003f1db6fe98487b0052",
    "tokenizer_config.json": "5df181fba586b7cb37d429c13c4f96cb43fb11de7bb6489733d9eded32418179",
    "vocab.json": "f1832ca38f7aa158b9a944ff583e4901e6b37d9d4ad9241f03838e636e9cfb03",
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
                model_label="英中翻譯模型",
            )

        if not is_verified_translation_model(temporary):
            raise RuntimeError("英中翻譯模型檔案不完整")
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
