#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$PROJECT_ROOT/.venv/bin/python}"
APP_PATH="$PROJECT_ROOT/dist/YT Downloader by 學人新創.app"
ZIP_PATH="$PROJECT_ROOT/dist/YT-Downloader-0.1.6-dev-macOS-arm64.zip"
PACKAGE_DIR=""

cleanup() {
    if [[ -n "$PACKAGE_DIR" && -d "$PACKAGE_DIR" ]]; then
        rm -rf "$PACKAGE_DIR"
    fi
}
trap cleanup EXIT

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
"$SCRIPT_DIR/create_macos_icon.sh"
"$PYTHON_BIN" -m PyInstaller --noconfirm --clean packaging/macos-arm64.spec
codesign --verify --deep --strict "$APP_PATH"

PACKAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/yt-downloader-package.XXXXXX")"
ZIP_TEMP="$PACKAGE_DIR/$(basename "$ZIP_PATH")"
EXTRACT_DIR="$PACKAGE_DIR/extracted"

# Resource forks and extended attributes become thousands of AppleDouble files
# in a ZIP. When left beside signed bundle files, they invalidate the signature.
ditto -c -k --norsrc --noextattr --noqtn --noacl --keepParent "$APP_PATH" "$ZIP_TEMP"

if unzip -Z1 "$ZIP_TEMP" | grep -Eq '(^|/)\._|^__MACOSX/'; then
    echo "封裝失敗：ZIP 內含 AppleDouble 或 __MACOSX 中繼資料。" >&2
    exit 1
fi

mkdir -p "$EXTRACT_DIR"
ditto -x -k "$ZIP_TEMP" "$EXTRACT_DIR"
codesign --verify --deep --strict "$EXTRACT_DIR/$(basename "$APP_PATH")"
mv -f "$ZIP_TEMP" "$ZIP_PATH"

echo "已建立開發預覽：$APP_PATH"
echo "已建立壓縮檔：$ZIP_PATH"
echo "注意：目前只有 ad-hoc 簽章，尚未使用學人新創 Developer ID 公證。"
