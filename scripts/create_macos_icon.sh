#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$PROJECT_ROOT/assets/app-icon.png"
OUTPUT="$PROJECT_ROOT/assets/app-icon.icns"
WORK_DIR=""

cleanup() {
    if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "macOS ICNS 圖示必須在 macOS 上建立。" >&2
    exit 1
fi

if [[ ! -f "$SOURCE" ]]; then
    echo "找不到 App 圖示來源：$SOURCE" >&2
    exit 1
fi

WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/yt-downloader-icon.XXXXXX")"
ICONSET="$WORK_DIR/AppIcon.iconset"
mkdir -p "$ICONSET"

make_icon() {
    local size="$1"
    local filename="$2"
    sips -z "$size" "$size" "$SOURCE" --out "$ICONSET/$filename" >/dev/null
}

make_icon 16 icon_16x16.png
make_icon 32 icon_16x16@2x.png
make_icon 32 icon_32x32.png
make_icon 64 icon_32x32@2x.png
make_icon 128 icon_128x128.png
make_icon 256 icon_128x128@2x.png
make_icon 256 icon_256x256.png
make_icon 512 icon_256x256@2x.png
make_icon 512 icon_512x512.png
make_icon 1024 icon_512x512@2x.png

iconutil -c icns "$ICONSET" -o "$OUTPUT"
echo "已建立 macOS 圖示：$OUTPUT"
