@echo off
chcp 65001 >nul
title YT Downloader by 學人新創

echo.
echo ═══════════════════════════════════════
echo   YT Downloader by 學人新創 啟動中...
echo ═══════════════════════════════════════
echo.

cd /d "%~dp0"

REM 啟動 Python 伺服器
echo [1/2] 啟動本機伺服器...
start /b .venv\Scripts\python app.py
timeout /t 3 /nobreak >nul

echo [2/2] 啟動固定網址隧道...
echo.
echo ───────────────────────────────────────
echo  對方用這個網址就能使用：
echo  （等幾秒會自動顯示）
echo ───────────────────────────────────────
echo.

tailscale funnel 8000

pause
