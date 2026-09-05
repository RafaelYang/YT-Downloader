# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "YT Downloader by 學人新創"

datas = [
    (str(PROJECT_ROOT / "static"), "static"),
    (str(PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (
        str(PROJECT_ROOT / "vendor" / "bgutil-ytdlp-pot-provider"),
        "pot-provider",
    ),
    (
        str(PROJECT_ROOT / "vendor" / "macos-arm64" / "node-LICENSE"),
        "licenses",
    ),
]
datas += collect_data_files("whisper")
datas += collect_data_files("opencc")

binaries = [
    (str(PROJECT_ROOT / "vendor" / "macos-arm64" / "ffmpeg"), "tools"),
    (str(PROJECT_ROOT / "vendor" / "macos-arm64" / "ffprobe"), "tools"),
    (str(PROJECT_ROOT / "vendor" / "macos-arm64" / "node"), "tools"),
]

provider_release = (
    PROJECT_ROOT
    / "vendor"
    / "bgutil-ytdlp-pot-provider"
    / "server"
    / "node_modules"
    / "canvas"
    / "build"
    / "Release"
)
binaries += [
    (
        str(path),
        "pot-provider/server/node_modules/canvas/build/Release",
    )
    for path in provider_release.iterdir()
    if path.suffix in {".node", ".dylib"}
]

hiddenimports = [
    "pystray._darwin",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "sentencepiece",
    "sacremoses",
]
hiddenimports += [
    module
    for module in collect_submodules("transformers.models.marian")
    if ".modeling_flax_" not in module and ".modeling_tf_" not in module
]

a = Analysis(
    [str(PROJECT_ROOT / "desktop_app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    module_collection_mode={"torch._numpy": "py"},
    excludes=["_pytest", "httpx", "IPython", "matplotlib", "pytest", "tensorboard"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch="arm64",
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    bundle_identifier="tw.xueren.yt-downloader",
    info_plist={
        "CFBundleDisplayName": APP_NAME,
        "CFBundleName": APP_NAME,
        "CFBundleShortVersionString": "0.1.4",
        "CFBundleVersion": "4",
        "LSMinimumSystemVersion": "13.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
)
