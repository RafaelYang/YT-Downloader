# YT Downloader by 學人新創 — Windows 說明

## 一般使用者安裝

Windows 使用者不需要安裝 Python、FFmpeg、Node.js 或 Tailscale。

1. 從私人 GitHub 專案的 Releases 下載
   `YT-Downloader-by-Xueren-0.1.0-dev-Windows-x64-Setup.exe`。
2. 執行安裝程式。安裝位置預設為目前使用者的 Local AppData，因此不需要
   系統管理員權限。
3. 安裝完成後啟動 App。操作頁面會在預設瀏覽器開啟，背景程式則常駐於
   Windows 系統列。
4. 第一次啟動會設定登入 Windows 後自動執行。可從系統列選單取消或重新開啟
   「登入後自動啟動」。

目前是未簽章的私人開發預覽版，Windows SmartScreen 可能顯示「未知的發行者」。
正式提供一般使用者前，仍應使用學人新創的 Windows 程式碼簽章憑證簽署安裝程式。

### 系統需求

- Windows 10／11 x64。
- 第一次產生逐字稿時需要網路下載 Whisper `small` 模型。
- 使用期間電腦必須保持開機；成品只會儲存在使用者自己的「下載」資料夾。

### 系統列功能

- 開啟 YT Downloader。
- 開啟下載資料夾。
- 開啟或關閉登入後自動啟動。
- 結束背景程式。

### 解除安裝

到「設定 → 應用程式 → 已安裝的應用程式」移除
`YT Downloader by 學人新創`。解除安裝程式會一併移除登入自動啟動設定，
但不會刪除使用者已下載的影片、音檔或逐字稿。

## 開發者本機執行

在 Windows x64 的 PowerShell 中：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python desktop_app.py --no-autostart
```

也可以按兩下 `start.bat` 啟動已建立好的開發環境。這個流程只監聽
`127.0.0.1`，不會建立對外公開的網路隧道。

## Windows x64 建置

Windows runtime 下載器會取得固定版本並驗證 SHA-256，內容包括 FFmpeg、
FFprobe、Node.js 與 loopback-only PO-token provider：

```powershell
.venv\Scripts\python -m pytest -q
.\scripts\fetch_windows_runtime.ps1
.\scripts\build_windows.ps1 -Python .venv\Scripts\python.exe
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" ".\packaging\windows-x64.iss"
```

安裝程式輸出：

```text
dist\installer\YT-Downloader-by-Xueren-0.1.0-dev-Windows-x64-Setup.exe
```

GitHub Actions 的 `Build Windows preview` 工作會在 `windows-2022` x64 環境
執行來源測試、PyInstaller 封裝後的本機 API 冒煙測試、Inno Setup 安裝包建置、
SHA-256 產生，並可將通過驗證的安裝程式附加到既有私人 prerelease。

## 尚需實機驗收

GitHub Windows runner 的成功建置不能取代實際使用者電腦測試。正式發布前仍須在
乾淨的 Windows 10 與 Windows 11 x64 電腦逐項確認：

- 安裝與解除安裝不要求管理員權限。
- 系統列與登入自動啟動正常。
- 第二次開啟不會產生重複背景程序。
- MP4 各畫質、MP3、逐字稿及開啟資料夾正常。
- 重新登入 Windows 後服務會自動啟動。
- SmartScreen 與程式碼簽章流程符合發布需求。
