#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESTINATION="$PROJECT_ROOT/vendor/macos-arm64"
TEMP_DIR="$(mktemp -d)"

FFMPEG_URL="https://ffmpeg.martin-riedl.de/download/macos/arm64/1787073674_9.0.1/ffmpeg.zip"
FFPROBE_URL="https://ffmpeg.martin-riedl.de/download/macos/arm64/1787073674_9.0.1/ffprobe.zip"
FFMPEG_SHA256="8287a1b2229e05eb41859f073e18e6c52c60a778f2f5e6881070fe51b79407fe"
FFPROBE_SHA256="102a26b8940a053298d9929bfaae71e4b6ef65ba5f19a99a88c433108560741a"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

download_and_verify() {
    local url="$1"
    local expected="$2"
    local archive="$3"
    local binary="$4"

    curl --fail --location --silent --show-error "$url" --output "$TEMP_DIR/$archive"
    local actual
    actual="$(shasum -a 256 "$TEMP_DIR/$archive" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        echo "SHA-256 驗證失敗：$archive" >&2
        exit 1
    fi

    ditto -x -k "$TEMP_DIR/$archive" "$TEMP_DIR/$binary-extracted"
    local extracted
    extracted="$(find "$TEMP_DIR/$binary-extracted" -type f -name "$binary" -print -quit)"
    if [[ -z "$extracted" ]]; then
        echo "壓縮檔中找不到 $binary" >&2
        exit 1
    fi
    install -m 755 "$extracted" "$DESTINATION/$binary"
}

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "這個工具下載器只支援 Apple Silicon macOS。" >&2
    exit 1
fi

mkdir -p "$DESTINATION"
download_and_verify "$FFMPEG_URL" "$FFMPEG_SHA256" "ffmpeg.zip" "ffmpeg"
download_and_verify "$FFPROBE_URL" "$FFPROBE_SHA256" "ffprobe.zip" "ffprobe"

file "$DESTINATION/ffmpeg"
file "$DESTINATION/ffprobe"
"$DESTINATION/ffmpeg" -version | head -n 1
"$DESTINATION/ffprobe" -version | head -n 1
