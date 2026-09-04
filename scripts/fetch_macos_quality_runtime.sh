#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TOOLS_DESTINATION="$PROJECT_ROOT/vendor/macos-arm64"
PROVIDER_DESTINATION="$PROJECT_ROOT/vendor/bgutil-ytdlp-pot-provider"
TEMP_DIR="$(mktemp -d)"

NODE_VERSION="24.20.0"
NODE_ARCHIVE="node-v${NODE_VERSION}-darwin-arm64.tar.xz"
NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/${NODE_ARCHIVE}"
NODE_SHA256="b7bf7707070b950ba1ec5f1af3bb6de0f2b1962c5033973d94068ab021ef3014"

PROVIDER_VERSION="1.3.2"
PROVIDER_ARCHIVE="bgutil-ytdlp-pot-provider-${PROVIDER_VERSION}.tar.gz"
PROVIDER_URL="https://codeload.github.com/Brainicism/bgutil-ytdlp-pot-provider/tar.gz/refs/tags/${PROVIDER_VERSION}"
PROVIDER_SHA256="3545ac7ffc0869498755cb3b4760a72fa2f176689d0890a6f5b898d163012ba2"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

verify_sha256() {
    local filepath="$1"
    local expected="$2"
    local actual
    actual="$(shasum -a 256 "$filepath" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        echo "SHA-256 驗證失敗：$(basename "$filepath")" >&2
        exit 1
    fi
}

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
    echo "這個相容元件下載器只支援 Apple Silicon macOS。" >&2
    exit 1
fi

curl --fail --location --silent --show-error "$NODE_URL" --output "$TEMP_DIR/$NODE_ARCHIVE"
curl --fail --location --silent --show-error "$PROVIDER_URL" --output "$TEMP_DIR/$PROVIDER_ARCHIVE"
verify_sha256 "$TEMP_DIR/$NODE_ARCHIVE" "$NODE_SHA256"
verify_sha256 "$TEMP_DIR/$PROVIDER_ARCHIVE" "$PROVIDER_SHA256"

tar -xf "$TEMP_DIR/$NODE_ARCHIVE" -C "$TEMP_DIR"
mkdir -p "$TEMP_DIR/provider"
tar -xzf "$TEMP_DIR/$PROVIDER_ARCHIVE" --strip-components=1 -C "$TEMP_DIR/provider"
patch -d "$TEMP_DIR/provider" -p1 < "$SCRIPT_DIR/patches/bgutil-localhost.patch"

NODE_ROOT="$TEMP_DIR/node-v${NODE_VERSION}-darwin-arm64"
(
    cd "$TEMP_DIR/provider/server"
    PATH="$NODE_ROOT/bin:/usr/bin:/bin" npm ci
    PATH="$NODE_ROOT/bin:/usr/bin:/bin" npx tsc
    PATH="$NODE_ROOT/bin:/usr/bin:/bin" npm prune --omit=dev
)

if ! file "$NODE_ROOT/bin/node" | grep -q "arm64"; then
    echo "下載的 Node.js 不是 Apple Silicon arm64。" >&2
    exit 1
fi
if ! file "$TEMP_DIR/provider/server/node_modules/canvas/build/Release/canvas.node" | grep -q "arm64"; then
    echo "下載的 Canvas 原生模組不是 Apple Silicon arm64。" >&2
    exit 1
fi
if ! grep -q 'host: "127.0.0.1"' "$TEMP_DIR/provider/server/build/main.js"; then
    echo "PO Token 供應器未限制在 loopback。" >&2
    exit 1
fi

mkdir -p "$TOOLS_DESTINATION"
install -m 755 "$NODE_ROOT/bin/node" "$TOOLS_DESTINATION/node"
install -m 644 "$NODE_ROOT/LICENSE" "$TOOLS_DESTINATION/node-LICENSE"

if [[ -e "$PROVIDER_DESTINATION" ]]; then
    rm -rf "$PROVIDER_DESTINATION"
fi
ditto "$TEMP_DIR/provider" "$PROVIDER_DESTINATION"

file "$TOOLS_DESTINATION/node"
file "$PROVIDER_DESTINATION/server/node_modules/canvas/build/Release/canvas.node"
"$TOOLS_DESTINATION/node" --version
echo "已準備 bgutil-ytdlp-pot-provider ${PROVIDER_VERSION}（僅監聽 127.0.0.1）。"
