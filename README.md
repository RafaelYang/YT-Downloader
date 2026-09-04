# YT Downloader by 學人新創

在使用者自己的電腦上執行的 YouTube 公開影片處理工具。目前功能包括
可選畫質的 MP4、MP3 與本機 Whisper 逐字稿。MP4 預設選最高畫質，每個
選項會顯示 yt-dlp 中繼資料估算的合併檔案大小；完成後可直接在頁面中從
本機預覽，不會將成品上傳雲端。請只處理自己擁有、已獲授權或平台允許
下載的內容。

桌面版完成處理後會直接存入「下載項目」的 `影片標題_日期時間` 資料夾，並提供
「📂 開啟資料夾」按鈕直接用系統檔案管理員開啟該次成品位置。成品檔名統一為
`影片標題_影片_畫質.mp4`、`影片標題_音檔.mp3` 與
`影片標題_逐字稿.txt`。

## 目前狀態

- 網頁核心可在 Windows 與 macOS 本機執行。
- Apple Silicon 桌面啟動器已具備選單列、單一執行個體、loopback API
  憑證與 LaunchAgent 自動啟動。
- FFmpeg 9.0.1 arm64 已固定版本與 SHA-256，可納入開發預覽 App。
- 高畫質相容層使用固定版本的 Node.js 24.20.0 arm64 與
  bgutil-ytdlp-pot-provider 1.3.2；內部服務只監聽隨機 `127.0.0.1` 連接埠。
- `dist/` 已產出約 884 MB 的 `.app` 與約 304 MB 的 ZIP 開發預覽。
- Windows 10／11 x64 current-user 安裝程式已在 GitHub `windows-2022` Runner
  完成建置、封裝版啟動及安裝／啟動／解除安裝生命週期測試。
- 主程式自動更新、SQLite 背景工作與正式 Developer ID 公證尚未完成。
- Windows 預覽版尚未簽章，並仍待乾淨 Windows 10／11 實機完成功能驗收。

## 開發環境

專案現有 `.venv` 曾從另一個資料夾搬移，所以請使用
`.venv/bin/python -m ...`；不要直接執行 `.venv/bin/yt-dlp` 或
`.venv/bin/pyinstaller`，它們的 shebang 仍可能指向舊路徑。

安裝依賴：

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

執行測試：

```bash
.venv/bin/python -m pytest -q
node --check static/app.js
```

啟動桌面開發版（按 Control-C 結束）：

```bash
.venv/bin/python desktop_app.py --no-tray --no-autostart
```

正常啟動會開啟瀏覽器；加上 `--background` 可只在背景執行。開發模式不會
自動修改登入啟動設定。

## macOS Apple Silicon 建置

先取得並驗證固定版本的 FFmpeg 與高畫質相容元件，再建置：

```bash
scripts/fetch_macos_tools.sh
scripts/fetch_macos_quality_runtime.sh
scripts/build_macos.sh
```

`scripts/build_macos.sh` 在元件尚未存在時也會自動執行對應下載器。下載器會
驗證固定 SHA-256，並把供應器的 HTTP 監聽範圍修補為 `127.0.0.1` 後才打包。

輸出位置：

- `dist/YT Downloader by 學人新創.app`
- `dist/YT-Downloader-by-學人新創-0.1.0-dev-macOS-arm64.zip`

這個預覽包在目前開發機上採 ad-hoc 簽章。正式給一般使用者下載前，仍須
使用學人新創的 Apple Developer ID 對 App 與內含執行檔重新簽章、送 Apple
notarization，並用乾淨的 Apple Silicon Mac 執行 Gatekeeper、安裝、重新登入、
MP4、MP3 與逐字稿驗收。

## 私人測試版安裝

目前的 GitHub Release 是供受邀測試者使用的開發預覽版，包含 Windows 10／11
x64 與 macOS 13 以上 Apple Silicon 版本；Intel Mac 尚無可安裝版本。

Windows：

1. 下載 `YT-Downloader-by-Xueren-0.1.0-dev-Windows-x64-Setup.exe` 並執行。
2. 安裝在目前使用者的 Local AppData，不需要管理員權限；安裝完成後可由桌面
   或開始功能表啟動，程式會常駐系統列。
3. 預覽版尚未簽章，因此 SmartScreen 可能顯示「未知的發行者」；只應從此私人
   Release 下載，並先核對 `SHA256SUMS-windows.txt`。
4. 第一次正常啟動會設定登入後自動執行，可從系統列選單隨時關閉。

macOS：

1. 從私人 GitHub 專案的 Releases 下載 ZIP，解壓縮後將 App 移到「應用程式」。
2. 因預覽版尚未經 Apple 公證，第一次請在 Finder 對 App 按 Control 並選擇
   「打開」；若系統仍攔截，可到「系統設定 → 隱私權與安全性」選擇允許打開。
3. App 啟動後會在選單列常駐，並可設定登入後自動啟動；電腦必須保持開機，
   下載與逐字稿才會繼續執行。
4. 第一次產生逐字稿時需要下載 Whisper 模型，因此會比之後的使用久。

YouTube 可能依影片、帳號或網路環境限制擷取。請只處理自己擁有、已獲授權
或平台允許下載的內容。

## 桌面資料位置

- Windows 應用資料：`%LOCALAPPDATA%\學人新創\YT Downloader\`
- macOS 應用資料：`~/Library/Application Support/學人新創/YT Downloader/`
- Windows 完成成品：每次解析會在 `%USERPROFILE%\Downloads\` 建立資料夾。
- macOS 完成成品：每次解析會在 `~/Downloads/` 建立資料夾。資料夾例如
  `影片標題_260831_1405/`；同分鐘、同標題重複時依序加上 `_2`、`_3`。
- Windows 自動啟動：目前使用者的 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`。
- macOS 自動啟動：`~/Library/LaunchAgents/tw.xueren.yt-downloader.plist`。

封裝版首次正常啟動會建立 LaunchAgent；選單列可關閉「登入後自動啟動」。
原始碼開發版若要測試，可明確執行：

```bash
.venv/bin/python desktop_app.py --install-autostart
.venv/bin/python desktop_app.py --remove-autostart
```

## 安全邊界

- 桌面 API 只監聽 `127.0.0.1`。
- 高畫質 PO Token 供應器只監聽隨機的 `127.0.0.1` 連接埠，且其輸出不寫入
  應用程式日誌，避免留下短效權杖。
- 啟動器每次產生隨機憑證，以 HttpOnly、SameSite cookie 保護 API。
- 只接受明確的 `youtube.com`／`youtu.be` HTTPS 主機名稱。
- 成品下載只能使用伺服器已登記的 job output，不能拼接任意檔案路徑。
- Cookie 上傳介面與 Docker Cookie 打包已移除；既有本機 Cookie 檔不會被程式讀取。

完整產品、更新與驗收設計請見 [DESKTOP_APP_DESIGN.md](DESKTOP_APP_DESIGN.md)。
第三方元件資訊請見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 2026-08-31 驗證紀錄

- `41 passed`，另有一項 FastAPI TestClient 上游棄用警告。
- 封裝後主程式、FFmpeg、FFprobe 都是 Mach-O arm64。
- 使用 Creative Commons 測試素材 `9UjexPhnxro`，封裝版成功產生可由 FFprobe
  讀取的 MP4、MP3，以及 Whisper `small` MPS 的 TXT 逐字稿。
- 以全新 App 資料夾驗證：封裝版會先驗證並沿用既有 Whisper 快取；若沒有
  可用快取，改用 macOS 系統 HTTPS／憑證鏈下載，再以官方 SHA-256 驗證。
  實測系統下載及首次逐字稿均成功，未停用 TLS 憑證驗證。
- 同一工作產生的 TXT、MP4、MP3 會共用 `影片標題_YYMMDD_HHMM` 資料夾；
  同一分鐘重複時會依序配置 `_2`、`_3`，不會覆蓋既有資料夾。
- 以 macOS LaunchServices 實測背景程序的重新開啟事件：再次開啟 `.app` 會由
  同一程序顯示操作頁面，不會靜默無反應，也不會產生第二個服務程序。
- 內建瀏覽器完成 MP3 後，「另存一份」與「開啟資料夾」按鈕版面正常；實際
  點擊開啟資料夾回報成功。API 只接受該工作已登記的完成檔案。
- 內建瀏覽器在封裝版確認：自訂畫質彈窗預設 1080p，並以設計過的選項卡
  顯示 1080p、720p、360p、144p 的預估大小；選 720p 後，FFprobe 與頁面播放器都讀到
  1280×720／60fps。程式會在儲存前用 FFprobe 核對實際高度，絕不把較低
  畫質冒充成使用者選擇的畫質。
- 完成 MP4 後會顯示本機影片播放器；網址輸入欄仍可直接解析下一支影片，
  原本頁面下方的「再下載一個」已移除。
- 封裝版實際下載 720p 後，磁碟檔名與 HTTP 下載回應均採
  `影片標題_影片_720p.mp4`；MP3 與逐字稿分別使用 `_音檔.mp3` 與
  `_逐字稿.txt`。
- App 通過 `codesign --verify --deep --strict` 與 ZIP 完整性檢查；`spctl`
  仍會拒絕 ad-hoc 簽章，符合「尚未公證的開發預覽」預期。

## 2026-09-04 Windows 驗證紀錄

- GitHub Actions `windows-2022` x64 工作通過 `45 passed`、Python 編譯檢查與
  JavaScript 語法檢查。
- 固定並核對 Windows FFmpeg／FFprobe、Node.js 24.20.0 與 loopback-only
  bgutil-ytdlp-pot-provider 1.3.2 後，PyInstaller 封裝版實際啟動且本機 API
  健康檢查成功。
- 繁體中文 Inno Setup current-user 安裝程式完成靜默安裝、從安裝目錄啟動、
  本機 API 健康檢查、Windows 使用者層登入自啟登錄的建立／移除與解除安裝；
  解除安裝後程式目錄已移除。
- Release 安裝檔大小為 290,794,932 bytes，SHA-256 為
  `aea5fdb0ef78b8121c4f3019d7f26ac9fce44ff2d73a140983fa971f7f4462d1`。
- Windows 系統列、重新登入，以及實際 MP4／MP3／逐字稿仍須在乾淨的
  Windows 10／11 實機驗收；目前不得視為已簽章正式版。
