# YT Downloader by 學人新創

在使用者自己的電腦上執行的 YouTube 公開影片處理工具。目前功能包括
可選畫質的 MP4、MP3 與本機 AI 逐字稿。逐字稿可選繁體中文或
English＋繁中，兩者都有時間碼分段；英文模式每段先顯示英文原文，再顯示
繁中翻譯。MP4 預設選最高畫質，每個
選項會顯示 yt-dlp 中繼資料估算的合併檔案大小；完成後可直接在頁面中從
本機預覽，不會將成品上傳雲端。請只處理自己擁有、已獲授權或平台允許
下載的內容。

桌面版完成處理後會直接存入「下載項目」的 `影片標題_日期時間` 資料夾，並提供
「📂 開啟資料夾」按鈕直接用系統檔案管理員開啟該次成品位置。成品檔名統一為
`影片標題_影片_畫質.mp4`、`影片標題_音檔.mp3` 與
`影片標題_逐字稿_繁中.txt` 或 `影片標題_逐字稿_英文雙語.txt`。

## 下載安裝程式

一般使用者請從 [YT-Downloader Google 雲端硬碟](https://drive.google.com/drive/folders/1Y4tBWJJzqqnewNeZWbWIeTxHY1m-3Kg4)
下載最新的雙平台安裝檔：

- macOS Apple Silicon：`YT-Downloader-0.1.4-dev-macOS-arm64.zip`
- Windows 10／11 x64：`YT-Downloader-0.1.4-dev-Windows-x64-Setup.exe`

私人 [GitHub Release v0.1.4-dev](https://github.com/RafaelYang/YT-Downloader/releases/tag/v0.1.4-dev)
保留給受邀的開發與測試成員，GitHub 會在安裝檔右側顯示 SHA-256。
頁面最下方的 `Source code (zip)` 與 `Source code (tar.gz)` 是 GitHub 自動產生的
原始碼，不是安裝檔；一般使用者不需要下載。

本機重新下載的測試包統一放在「下載項目 → YT Downloader Google Drive 上傳 →
版本號」資料夾，與程式產生的影片資料夾分開。此 GitHub 專案保持私人，
只有已獲邀的 GitHub 帳號能開啟原始碼與 Release；Google Drive 資料夾則供
知道連結的使用者唯讀下載安裝檔。

## 目前狀態

- 網頁核心可在 Windows 與 macOS 本機執行。
- Apple Silicon 桌面啟動器已具備選單列、單一執行個體與 loopback API
  憑證；只在使用者手動開啟 App 時執行。
- FFmpeg 9.0.1 arm64 已固定版本與 SHA-256，可納入開發預覽 App。
- 高畫質相容層使用固定版本的 Node.js 24.20.0 arm64 與
  bgutil-ytdlp-pot-provider 1.3.2；內部服務只監聽隨機 `127.0.0.1` 連接埠。
- `dist/` 已產出 macOS Apple Silicon App 與 394,897,651 bytes 的 ZIP 開發預覽。
- Windows 10／11 x64 current-user 安裝程式已在 GitHub `windows-2022` Runner
  完成建置、封裝版啟動及安裝／啟動／解除安裝生命週期測試。
- MP4 會優先使用 H.264／AAC；若所選畫質只有 AV1／VP9，儲存前會自動
  轉為 H.264／AAC MP4，避免 QuickTime 只播放聲音。
- 逐字稿使用 Whisper `turbo`；繁中模式會轉成台灣繁體用字，英文模式另用
  本機英中模型逐段翻譯，不需付費 API。
- 缺少逐字稿模型時，開始前會先列出所需模型與預估下載容量；使用者選擇
  「暫不下載」即取消流程，不會建立下載或逐字稿工作。
- 主程式自動更新、SQLite 背景工作與正式 Developer ID 公證尚未完成。
- Windows 預覽版尚未簽章，並仍待乾淨 Windows 10／11 實機完成功能驗收。

## 開發環境

建議在專案根目錄建立 `.venv`，並使用 `.venv/bin/python -m ...`
執行 Python 工具，避免依賴系統 Python 環境。

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
.venv/bin/python desktop_app.py --no-tray
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
- `dist/YT-Downloader-0.1.4-dev-macOS-arm64.zip`

這個預覽包在目前開發機上採 ad-hoc 簽章。正式給一般使用者下載前，仍須
使用學人新創的 Apple Developer ID 對 App 與內含執行檔重新簽章、送 Apple
notarization，並用乾淨的 Apple Silicon Mac 執行 Gatekeeper、安裝、重新登入、
MP4、MP3 與逐字稿驗收。

## 私人測試版安裝

目前的 GitHub Release 是供受邀測試者使用的開發預覽版，包含 Windows 10／11
x64 與 macOS 13 以上 Apple Silicon 版本；Intel Mac 尚無可安裝版本。

Windows：

1. 下載 `YT-Downloader-0.1.4-dev-Windows-x64-Setup.exe` 並執行。
2. 安裝在目前使用者的 Local AppData，不需要管理員權限；安裝完成後可由桌面
   或開始功能表啟動，程式會常駐系統列。
3. 預覽版尚未簽章，因此 SmartScreen 可能顯示「未知的發行者」；只應從此私人
   Release 下載，並先核對 `SHA256SUMS-windows.txt`。
4. 程式只會在使用者從桌面或開始功能表手動開啟後執行，不會隨登入 Windows 自動啟動。

macOS：

1. 從私人 GitHub 專案的 Releases 下載 ZIP，解壓縮後將 App 移到「應用程式」。
2. 因預覽版尚未經 Apple 公證，第一次請在 Finder 對 App 按 Control 並選擇
   「打開」；若系統仍攔截，可到「系統設定 → 隱私權與安全性」選擇允許打開。
3. App 只會在使用者手動開啟後於選單列常駐，不會隨登入 macOS 自動啟動；
   執行下載或逐字稿期間，電腦與 App 都必須保持運作。
4. 第一次產生逐字稿時需要下載約 1.6 GB 的 Whisper `turbo` 模型；第一次使用
   英文雙語模式另需下載約 308 MB 的英中翻譯模型，因此會比之後的使用久。

YouTube 可能依影片、帳號或網路環境限制擷取。請只處理自己擁有、已獲授權
或平台允許下載的內容。

## 桌面資料位置

- Windows 應用資料：`%LOCALAPPDATA%\學人新創\YT Downloader\`
- macOS 應用資料：`~/Library/Application Support/學人新創/YT Downloader/`
- Windows 完成成品：每次解析會在 `%USERPROFILE%\Downloads\` 建立資料夾。
- macOS 完成成品：每次解析會在 `~/Downloads/` 建立資料夾。資料夾例如
  `影片標題_260831_1405/`；同分鐘、同標題重複時依序加上 `_2`、`_3`。
- `0.1.1-dev` 起不再建立 Windows Run 登錄或 macOS LaunchAgent；新版首次啟動會清除舊預覽版留下的登入自動啟動設定。

若要手動清理舊版設定，可執行：

```bash
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

## 2026-09-05 手動啟動版驗證紀錄

- 本機測試通過 `45 passed`、Python 編譯檢查與 JavaScript 語法檢查。
- macOS `0.1.1-dev` 封裝版只在手動開啟後執行；啟動時成功清除刻意建立的
  舊版 LaunchAgent 與自動啟動偏好，結束後未留下主程式或 PO-token provider。
- macOS ZIP 大小為 307,641,726 bytes，SHA-256 為
  `c4ff8f44d6ea22194eedf729d07344bd09fbced1d022c5b0935a84da2d99c6a7`；
  App 通過 `codesign --verify --deep --strict`，ZIP 通過完整性檢查。
- GitHub Actions Windows x64 工作 `33944432189` 通過 `45 passed`、Python
  編譯檢查與 JavaScript 語法檢查。
- 固定並核對 Windows FFmpeg／FFprobe、Node.js 24.20.0 與 loopback-only
  bgutil-ytdlp-pot-provider 1.3.2 後，PyInstaller 封裝版實際啟動且本機 API
  健康檢查成功。
- 繁體中文 Inno Setup current-user 安裝程式完成靜默安裝、從安裝目錄啟動、
  本機 API 健康檢查、舊版登入自啟登錄的清除與解除安裝；新版未重新建立
  登入自啟登錄，解除安裝後程式目錄已移除。
- Windows Release 安裝檔大小為 290,815,651 bytes，SHA-256 為
  `3a66581ba9a30beb7875aa2dc6001ac3340ca5fda01c63981f4feadd7a92df49`；
  從 GitHub Release 重新下載後核對一致。
- Windows 系統列、重新登入，以及實際 MP4／MP3／逐字稿仍須在乾淨的
  Windows 10／11 實機驗收；目前不得視為已簽章正式版。

## 2026-09-05 影片相容性修正

- 重現 QuickTime 只播放聲音的檔案為 AV1 視訊與 AAC 音訊，不是下載檔損壞。
- 畫質選擇器改為同解析度下優先 H.264／AAC，不會為了相容性降低畫質。
- 完成後再用 FFprobe 核對畫質、編碼與像素格式；AV1／VP9 或非 AAC 音訊
  會以內附 FFmpeg 轉成 H.264／AAC、yuv420p 的 MP4 後才發布。
- `48 passed`，並以合成 AV1／Opus 影片驗證自動轉檔與完整解碼。
- `0.1.2-dev` macOS 封裝版實際解析及下載 YouTube 公開測試片，成品為
  H.264／AAC、yuv420p MP4，高度、檔名、儲存目錄與全片解碼均通過。
- 使用回報問題的同一支 8:12 影片重新下載 1080p，輸出為 1920×1080、
  H.264／AAC、yuv420p；FFmpeg 全片解碼與 macOS Quick Look 縮圖產生均成功。
- macOS ZIP 大小為 353,668,609 bytes，SHA-256 為
  `a2899cb07b20d1bc8c4c851975f15f252b11c8e88fba4c7b8ea15c96e3aa5b7f`；
  App 通過 `codesign --verify --deep --strict`，ZIP 通過完整性檢查。
- GitHub Actions Windows x64 工作 `33957014788` 通過 `48 passed`、封裝後啟動、
  Inno Setup 安裝、手動啟動、舊版登入自啟清理與解除安裝生命週期。
- Windows 安裝檔大小為 290,790,989 bytes，SHA-256 為
  `c6d06beaea88a4f7500b138089c3d0790881c896989ef6b1f62d0e48e71210c0`。

## 2026-09-05 多語逐字稿升級

- Whisper 從 `small` 升級為 `turbo`，繁中與英文都依 Whisper 原生時間段落
  輸出時間碼；繁中模式會套用台灣繁體用字轉換。
- 英文模式以固定版本、逐檔 SHA-256 驗證的離線 OPUS-MT 模型翻譯，每段固定
  先顯示英文原文，再顯示繁中翻譯。
- 合成英文與台灣華語音訊均通過完整 SSE 工作、檔名、下載資料夾及 TXT 內容
  驗證；英文模式也在最終 macOS App 內實際載入權重並完成推論。
- `54 passed`，Python 編譯、JavaScript 語法、PyInstaller AI 元件自我檢查、
  App 深層簽章驗證與 ZIP 完整性檢查均通過。
- macOS ZIP 大小為 394,897,651 bytes，SHA-256 為
  `e62795f08ef4bf19aa394beb12fa220f8dd9f3af10a0afe587024a758778cdfd`。
- Windows GitHub Actions run `33962467334` 通過 54 項測試、封裝後 AI 元件
  自我檢查、本機 API 健康檢查，以及安裝／啟動／舊版自啟清理／解除安裝流程。
- Windows 安裝檔大小為 316,634,892 bytes，SHA-256 為
  `8d3dfcf47182707829219f2e65fb89a87ba2e656879c4e7e56f299549c2a6cf9`。
- 測試期間 YouTube 對公開短片回傳反機器人阻擋，因此本次沒有把線上影片的
  完整下載／逐字稿列為通過；仍須以使用者網路環境的公開影片再次驗收。

## 2026-09-05 首次模型下載確認

- 開始逐字稿前會先驗證本機模型；檢查本身不會下載檔案。
- 只有缺少模型時才顯示自訂確認視窗，逐一列出模型名稱、預估容量及合計容量。
- 「暫不下載」、點選背景或按 Escape 都會取消，不建立逐字稿 SSE 連線；只有
  「下載並繼續」會開始原有的音訊下載與模型安裝流程。
- `59 passed`，且內建瀏覽器驗證取消後的逐字稿呼叫數為 0、同意後才變成 1。
- 乾淨的封裝環境驗證能列出 Whisper turbo 約 1.6 GB 與英中翻譯模型約
  315 MB；狀態檢查完成後模型資料夾仍為空，未在使用者同意前下載檔案。
- macOS ZIP 大小為 394,903,025 bytes，SHA-256 為
  `f7ffca254e56508091912c3fc7eb51b9684e9831764b7d2baeb1db617cf5cbd2`；
  App 深層簽章、ZIP 完整性、封裝啟動與 AI 元件自我檢查均通過。
- Windows GitHub Actions run `33964382471` 通過 59 項測試、封裝後啟動、
  Inno Setup 安裝、手動啟動、舊版自啟清理與解除安裝生命週期。
- Windows 安裝檔大小為 316,618,922 bytes，SHA-256 為
  `eaded6f0594d1f03038f582d5e7dd0c64569bbd5d28b43d5f2be86f14e9c474c`。
