#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"
APP_PATH="$PROJECT_ROOT/dist/YT Downloader by 學人新創.app"
ZIP_PATH="$PROJECT_ROOT/dist/YT-Downloader-0.1.2-dev-macOS-arm64.zip"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "macOS Apple Silicon App 必須在 arm64 Mac 上建置。" >&2
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "找不到 Python：$PYTHON_BIN" >&2
    exit 1
fi

if [[ ! -x "$PROJECT_ROOT/vendor/macos-arm64/ffmpeg" || ! -x "$PROJECT_ROOT/vendor/macos-arm64/ffprobe" ]]; then
    "$SCRIPT_DIR/fetch_macos_tools.sh"
fi

if [[ ! -x "$PROJECT_ROOT/vendor/macos-arm64/node" || ! -f "$PROJECT_ROOT/vendor/bgutil-ytdlp-pot-provider/server/build/main.js" ]]; then
    "$SCRIPT_DIR/fetch_macos_quality_runtime.sh"
fi

if ! file "$PROJECT_ROOT/vendor/macos-arm64/ffmpeg" | grep -q "arm64"; then
    echo "內附的 FFmpeg 不是 Apple Silicon arm64。" >&2
    exit 1
fi

if ! file "$PROJECT_ROOT/vendor/macos-arm64/node" | grep -q "arm64"; then
    echo "內附的 Node.js 不是 Apple Silicon arm64。" >&2
    exit 1
fi

cd "$PROJECT_ROOT"
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean packaging/macos-arm64.spec
codesign --verify --deep --strict "$APP_PATH"
ditto -c -k --keepParent "$APP_PATH" "$ZIP_PATH"

echo "已建立開發預覽：$APP_PATH"
echo "已建立壓縮檔：$ZIP_PATH"
echo "注意：目前只有 ad-hoc 簽章，尚未使用學人新創 Developer ID 公證。"
