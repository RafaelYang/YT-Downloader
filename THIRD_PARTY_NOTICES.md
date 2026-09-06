# Third-party notices

`YT Downloader by 學人新創` uses the following third-party projects. This
file is an engineering inventory, not legal advice. A public release must ship
the applicable license texts and satisfy source-availability requirements.

## FFmpeg and FFprobe

- Version used by the Apple Silicon preview: 9.0.1
- Binary provider: <https://ffmpeg.martin-riedl.de/>
- Reproducible build scripts: <https://git.martin-riedl.de/ffmpeg/build-script>
- Version used by the Windows x64 preview: FFmpeg n8.1.2-50-g1a748fe2cd
- Windows binary provider and build scripts: <https://github.com/BtbN/FFmpeg-Builds>
- Upstream source: <https://ffmpeg.org/download.html>
- Build configuration includes `--enable-gpl --enable-version3`; the resulting
  binaries report GPLv3 or later.
- The Windows build bundles the binary archive's `LICENSE.txt`.

## yt-dlp

- Project: <https://github.com/yt-dlp/yt-dlp>
- License: The Unlicense

## bgutil-ytdlp-pot-provider

- Version: 1.3.2
- Project: <https://github.com/Brainicism/bgutil-ytdlp-pot-provider>
- License: GPL-3.0-only
- The complete tagged source and license are included in the App bundle.
- Local modification: `server/src/main.ts` is patched to listen only on
  `127.0.0.1` instead of wildcard IPv4/IPv6 addresses. The reproducible patch is
  shipped as `scripts/patches/bgutil-localhost.patch` in this source project.

## Node.js

- Version used by the Apple Silicon and Windows x64 previews: 24.20.0
- Project and source: <https://nodejs.org/en/about/get-involved>
- License: MIT; Node.js also bundles components under their respective licenses.
- The Node.js license is included with the App bundle.

## OpenAI Whisper

- Project: <https://github.com/openai/whisper>
- License: MIT

## Meta M2M100 multilingual translation model

- Model: `facebook/m2m100_418M`
- Pinned revision: `55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636`
- Project: <https://huggingface.co/facebook/m2m100_418M>
- License: MIT
- The application downloads and SHA-256 verifies the model on first use; the
  model is not embedded in the installer.

## Hugging Face Transformers, SentencePiece, Sacremoses, and OpenCC

- Transformers: <https://github.com/huggingface/transformers> (Apache-2.0)
- SentencePiece: <https://github.com/google/sentencepiece> (Apache-2.0)
- Sacremoses: <https://github.com/alvations/sacremoses> (MIT)
- OpenCC Python reimplementation:
  <https://github.com/yichen0831/opencc-python> (Apache-2.0)

## Inno Setup

- Project: <https://jrsoftware.org/isinfo.php>
- License permits use for commercial applications and redistribution subject to
  its stated conditions.
- The Windows installer uses a pinned, SHA-256-verified Traditional Chinese
  message file from the official Inno Setup source repository.

## FastAPI, Uvicorn, PyInstaller, pystray, Pillow, and JavaScript dependencies

Their license texts and exact versions must be collected into the release
artifact before this preview is distributed publicly.
