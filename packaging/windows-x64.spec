# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


PROJECT_ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "YT Downloader by 學人新創"
WINDOWS_VENDOR = PROJECT_ROOT / "vendor" / "windows-x64"
PROVIDER_ROOT = PROJECT_ROOT / "vendor" / "bgutil-ytdlp-pot-provider"

datas = [
    (str(PROJECT_ROOT / "static"), "static"),
    (str(PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"), "."),
    (str(PROVIDER_ROOT), "pot-provider"),
    (str(WINDOWS_VENDOR / "node-LICENSE"), "licenses"),
    (str(WINDOWS_VENDOR / "ffmpeg-LICENSE.txt"), "licenses"),
]
datas += collect_data_files("whisper")
datas += collect_data_files("opencc")

binaries = [
    (str(WINDOWS_VENDOR / "ffmpeg.exe"), "tools"),
    (str(WINDOWS_VENDOR / "ffprobe.exe"), "tools"),
    (str(WINDOWS_VENDOR / "node.exe"), "tools"),
]

hiddenimports = [
    "pystray._win32",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "sentencepiece",
    "sacremoses",
]
hiddenimports += [
    module
    for module in collect_submodules("transformers.models.m2m_100")
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
    icon=str(PROJECT_ROOT / "build" / "windows" / "app-icon.ico"),
    version=str(PROJECT_ROOT / "packaging" / "windows-version-info.txt"),
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
