@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo 找不到 Windows 開發環境，請先依照 SETUP_WINDOWS.md 建立 .venv。
    pause
    exit /b 1
)

start "YT Downloader by 學人新創" ".venv\Scripts\pythonw.exe" "desktop_app.py"
