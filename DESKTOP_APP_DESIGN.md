# YT Downloader by 學人新創

Windows 與 macOS 桌面版產品與技術設計 v1

狀態：Apple Silicon 與 Windows x64 `0.1.6-dev` 開發預覽進入建置驗證。Mac 版已在 Apple M2 Pro 驗證手動啟動與舊版 LaunchAgent 清理；Windows 版已在 GitHub Windows Runner 通過封裝版啟動、舊版登入自啟清理及安裝／啟動／解除安裝測試，但尚待乾淨 Windows 10／11 實機功能驗收。Developer ID 公證、Windows 程式碼簽章與自動更新仍未完成，因此還不是正式公開版。

截至 2026-09-05 的實作進度：

- 已完成 macOS 選單列啟動器、單一執行個體、本機資料路徑與 `127.0.0.1` 限制；程式只在使用者手動開啟後執行。
- 已完成 localhost 隨機憑證、Host／Origin 檢查、YouTube URL 白名單與已登記成品下載路徑。
- 已移除 Cookie 上傳介面及 Docker Cookie 打包，並修正逐字稿 DOM id。
- 已納入固定版本與雜湊的 Apple Silicon FFmpeg／FFprobe 9.0.1。
- 已納入固定版本與雜湊的 Node.js 24.20.0 arm64，以及只監聽 loopback 的
  bgutil-ytdlp-pot-provider 1.3.2 高畫質相容層。
- 已完成預設最高畫質、各畫質預估大小、實際輸出高度核對與本機 MP4 預覽。
- MP4 儲存前會核對編碼，優先 H.264／AAC；AV1／VP9 會自動轉為
  H.264／AAC MP4，以相容 macOS QuickTime 與 Windows 常見播放器。
- 已完成 Whisper `turbo` 的繁中時間碼分段，以及英文原文在前、繁中翻譯在後的
  離線雙語分段逐字稿。
- 已完成 Windows x64 PyInstaller 封裝、系統列、舊版登入自啟清理與繁中
  Inno Setup 安裝程式；Windows Runner 已通過完整安裝生命週期測試。
- 仍待完成 SQLite queue、工作取消／歷史、24 小時清理、自動更新／回復、
  正式簽章／公證，以及乾淨 Windows 10／11 實機功能驗收。

## 1. 產品定位

「YT Downloader by 學人新創」是一套在使用者自己的 Windows 或 Mac 電腦上執行的本機工具。使用者只需安裝一次；之後直接開啟 App 即可使用，不需要手動開伺服器、安裝 Python、執行批次檔或維護雲端主機，也不會隨登入系統自動啟動。

核心功能：

- 解析 YouTube 公開影片資訊。
- 選擇畫質並下載 MP4；預設最高畫質，顯示預估大小，完成後本機預覽。
- 下載並轉換 MP3。
- 使用本機 AI 產生「原文」或「原文＋繁中翻譯」的時間碼分段 TXT 逐字稿，
  原文語言由 Whisper 自動辨識。
- 自動更新程式與 yt-dlp，更新失敗時可回復上一版。

本產品只應用於使用者自有、已獲授權或平台明確允許下載的內容。

## 2. v1 範圍

### 包含

- Windows 10／11 x64。
- macOS Apple Silicon；第一個 Mac 驗收目標為目前開發機的 Apple M2 Pro。Intel Mac 待獨立建置與實機驗證後再列為正式支援。
- 單一使用者安裝，不要求系統管理員權限。
- 只有使用者手動開啟 App 時才啟動。
- Windows 系統列／macOS 選單列常駐圖示。
- 本機介面與本機處理。
- MP4、MP3、逐字稿三種工作。
- 工作進度、取消、失敗重試與歷史紀錄。
- 主程式、下載引擎、模型三層更新。
- 正常解除安裝；保留或刪除下載檔由使用者決定。

### 不包含

- 公開雲端下載服務。
- 從外網連回使用者電腦。
- 多人帳號、跨裝置同步或雲端備份。
- DRM、付費、私人或未獲授權內容的繞過功能。
- Mac App Store 發布；v1 採官網／GitHub Releases 直接散布。

## 3. 使用者體驗

### 第一次安裝

1. Windows 使用者執行 `YT-Downloader-0.1.6-dev-Windows-x64-Setup.exe`；Mac 使用者解壓縮 ZIP 並將 App 放入「應用程式」。
2. 首次啟動顯示授權資訊，並清除舊預覽版可能留下的登入自動啟動設定。
3. Windows 安裝至使用者的 Local AppData，不要求系統管理員權限；macOS 使用標準 `.app` bundle。
4. 首次啟動完成環境檢查，背景下載尚未安裝的語音模型並顯示進度。
5. 顯示主畫面與簡短的授權內容提醒。

### 日常使用

1. 使用者點桌面／應用程式捷徑，手動開啟 YT Downloader。
2. App 啟動後可從 Windows 系統列或 macOS 選單列再次開啟操作頁面。
3. 貼上網址，解析後選擇 MP4、MP3 或 AI 逐字稿。
4. 完成後可直接開啟檔案或所在資料夾。

只有使用者主動開啟 App 時顯示介面；執行後可在系統列／選單列常駐，直到使用者選擇結束。
macOS App 已在背景執行時，再次從 Finder 或 Dock 開啟必須處理系統的 reopen
事件並顯示操作頁面，不得因單一執行個體而靜默無反應。

### 系統列／選單列選單

- 開啟 YT Downloader
- 開啟下載資料夾
- 目前工作與進度
- 檢查更新
- 設定
- 結束

## 4. 品牌與介面

- 正式名稱：`YT Downloader by 學人新創`
- 主標：`YT Downloader`
- 品牌署名：`by 學人新創`
- 副標：`影片下載 · 音檔轉換 · AI 逐字稿`
- 視覺方向：沿用現有深色玻璃態介面與紫藍漸層，桌面版補齊 Windows 系統列、macOS 選單列與更新狀態。
- 圖示方向：圓角方形、播放三角形、紫藍漸層；16、32、48、128、256 像素均需清楚辨識。

## 5. 架構

```text
使用者手動開啟 App
   |
   v
Desktop Launcher / Tray  ----->  Updater Helper
   |                                  |
   | 啟動並監看                       | 驗證、替換、回復
   v                                  v
Local FastAPI (127.0.0.1 only) <---- Versioned app folders
   |
   +---- Static HTML/CSS/JS UI
   +---- Local PO-token provider (random 127.0.0.1 port)
   +---- SQLite job store
   +---- Background job worker
            |
            +---- yt-dlp executable + JS runtime
            +---- FFmpeg / FFprobe
            +---- Local transcription engine + model
```

### 元件責任

#### Desktop Launcher / Tray

- Windows 使用 named mutex，macOS 使用 process lock 保證同一使用者只執行一份。
- 啟動本機 API、等待健康檢查成功並維持系統列或選單列圖示。
- 第二次啟動時通知既有程序開啟主畫面，不另開伺服器。
- API 異常結束時有限次數自動重啟，持續失敗則顯示可理解的錯誤。

#### Local FastAPI

- 只監聽 `127.0.0.1`，不得監聽 `0.0.0.0`。
- 提供靜態介面、工作 API、進度事件與健康檢查。
- 不直接在 HTTP request 中執行長時間工作；request 只建立工作。

#### Background Worker

- 從 SQLite 讀取 queued 工作並執行。
- 預設同時一項下載／轉檔與一項逐字稿，避免壓垮一般電腦。
- 定期寫入進度，程式重啟後能標記並恢復可重試工作。
- 支援取消，並清除中間檔但保留已完成成品。

#### Updater Helper

- 與主程式分離，避免執行中的 EXE 無法替換自己。
- 只接受通過簽章與雜湊驗證的更新。
- 在沒有執行中工作時更新；逾時則延後，不強制中斷。
- 新版健康檢查失敗時切回上一版。

## 6. 本機資料位置

Windows：

```text
%LOCALAPPDATA%\Programs\YT Downloader by 學人新創\
  launcher.exe
  updater.exe
  current\
  versions\<app-version>\
  tools\
    yt-dlp.exe
    ffmpeg.exe
    ffprobe.exe
    js-runtime.exe

%LOCALAPPDATA%\學人新創\YT Downloader\
  app.db
  settings.json
  logs\
  models\
  updates\
  temp\

%USERPROFILE%\Downloads\<sanitized-title>_<YYMMDD_HHMM>\
  <finished files from one resolved video>
```

macOS：

```text
/Applications/YT Downloader by 學人新創.app

~/Library/Application Support/學人新創/YT Downloader/
  app.db
  settings.json
  logs/
  models/
  updates/
  temp/

~/Downloads/<sanitized-title>_<YYMMDD_HHMM>/
  <finished files from one resolved video>
```

- 程式、工具、資料、模型與使用者成品必須分開。
- 每次解析的 MP4、MP3、逐字稿共用一個時間資料夾；同分鐘已有同名資料夾時
  依序加上 `_2`、`_3`，不得覆寫既有成品。
- 更新不得覆寫 `app.db`、設定、模型或下載成品。
- `temp` 中超過 24 小時且未被工作引用的檔案可自動清理。
- 日誌預設保留 14 天，且不得記錄 Cookie、完整授權標頭或敏感查詢參數。

## 7. 工作與資料模型

SQLite 是單機版唯一的狀態來源，不需要另外安裝資料庫服務。

`jobs` 最少包含：

- `id`
- `type`: `resolve`、`mp4`、`mp3`、`transcript`
- `source_url`
- `status`: `queued`、`running`、`completed`、`failed`、`cancelled`
- `progress`
- `message`
- `output_path`
- `error_code`
- `created_at`、`started_at`、`finished_at`
- `engine_version`

工作錯誤應使用穩定的 `error_code`，畫面再轉換為繁體中文訊息；不可只把 yt-dlp 或 FFmpeg 原始例外直接顯示給使用者。

## 8. YouTube 與 Cookie 策略

- 預設不使用登入 Cookie，先處理一般公開影片。
- 只接受 `youtube.com` 與 `youtu.be` 的 HTTPS URL，避免任意 URL 造成 SSRF 或讀取本機檔案。
- 不再提供把 Cookie 上傳到伺服器的介面。
- 需要 YouTube PO Token 的公開影片格式，使用隨 App 啟停的本機供應器；服務
  只能監聽隨機 `127.0.0.1` 連接埠，且不得把產生的權杖寫入日誌。
- 畫質選擇必須是精確高度；下載後以 FFprobe 核對，絕不可悄悄降級後仍標示
  為使用者所選畫質。
- 若影片確實需要登入，設定頁可在明確告知風險後啟用「使用這台電腦的瀏覽器登入狀態」。
- 使用瀏覽器 Cookie 時應即時讀取，不產生長期 cookies.txt 副本；讀取失敗時不得降低系統安全設定。
- 日誌、SQLite、更新回報與錯誤回報都不得包含 Cookie。

本機住宅 IP 通常比雲端機房 IP 更適合 yt-dlp，但仍不承諾所有影片永久可解析。下載引擎必須可獨立更新與回復。

## 9. 逐字稿引擎

逐字稿引擎使用共同介面、依平台選擇最佳後端：Windows 優先評估 `faster-whisper` CPU INT8；Apple Silicon 優先評估 `whisper.cpp` Metal，並與現有 OpenAI Whisper MPS 實測比較。正式採用前必須在 Windows 10／11 與 Apple M2 Pro 實機驗證速度、繁體中文品質、記憶體與打包結果。

預設模型：

- 8 GB 以上記憶體：multilingual `small`。
- 低規格模式：multilingual `base`。
- 模型不存在時背景下載，顯示大小、進度與取消選項。
- 模型下載後驗證 SHA-256，失敗不得載入。

逐字稿工作不得阻塞下載工作或 UI；應獨立排隊並允許使用者稍後再開啟結果。

## 10. 三層更新設計

### 主程式

- 發布位置：GitHub Releases。
- 更新頻率：功能、安全或相容性修正時。
- 程式每天最多檢查一次，也可由使用者手動檢查。
- Windows 背景下載新版 Inno Setup 安裝包；macOS 背景下載對應架構的已簽章更新包。兩者都只在空閒時套用。
- 保留上一個可用版本，健康檢查失敗時自動回復。

### yt-dlp 與工具

- `yt-dlp.exe` 與主程式分開更新。
- 不讓所有使用者直接追未測試版本；發布端先核准版本，再更新 signed manifest。
- 更新後先執行版本與基本解析健康檢查，失敗立即回復。
- FFmpeg 與 JavaScript runtime 只在必要時更新，避免不必要的大型下載。

### 語音模型

- 模型有獨立版本、雜湊與相容的引擎版本範圍。
- 新模型驗證成功前保留舊模型。
- 模型更新失敗不應影響 MP4、MP3 功能。

### 更新安全

`latest.json` manifest 至少包含：

```json
{
  "channel": "stable",
  "version": "1.0.0",
  "platform": "windows-x64",
  "url": "https://github.com/.../releases/download/v1.0.0/setup.exe",
  "sha256": "...",
  "signature": "...",
  "minimum_supported_version": "1.0.0"
}
```

- Manifest 使用離線保存的 Ed25519 私鑰簽署，公開金鑰內嵌在 launcher。
- 僅有 SHA-256 不足以防止來源與檔案一起被竄改，必須同時驗證簽章。
- 更新檔下載至 staging，完整驗證後才能執行。
- 安裝器採目前使用者模式，避免每次更新跳 UAC。
- macOS 更新包與 App 內所有 executable 必須使用相同 Developer ID 簽署並完成 notarization；未簽署測試版不得宣稱能無警告自動更新。
- 除非是明確標示的高風險安全版本，更新不得中斷執行中的工作。

## 11. 本機安全基準

- API 僅限 loopback。
- 啟動時產生每位使用者專用的本機 session secret。
- 驗證 `Host`、`Origin`、SameSite session 與修改型 API 的 CSRF token，避免惡意網站呼叫 localhost API。
- 所有檔案下載都以 job id 查找資料庫紀錄，不接受使用者直接拼接任意路徑。
- 安全檔名處理後仍須驗證最終路徑位於允許的下載根目錄。
- URL 只允許 HTTPS 與明確 YouTube hostname。
- 更新、Cookie 與下載資料夾採最小權限。
- 移除 Docker image 與專案內的 Cookie 打包流程。

## 12. 打包與發布

- Python 應用採 PyInstaller `onedir`／macOS `.app` bundle，不採難以更新與除錯的巨大 `onefile`。
- Windows 安裝器採 Inno Setup，預設 current-user install。
- macOS 產出 Apple Silicon `.app` 與 `.dmg`；不建立 Login Item／LaunchAgent，選單列提供開啟與結束功能。
- `yt-dlp.exe`、FFmpeg、FFprobe、JS runtime 與授權文件作為獨立檔案散布。
- 發布頁與「關於」畫面必須列出第三方元件、版本與授權。
- 未購買程式碼簽章憑證前，測試版需清楚說明 Windows SmartScreen 可能顯示未知發行者。
- 未使用 Apple Developer ID 簽署與 notarize 前，macOS 測試版會有 Gatekeeper 首次啟動確認，不能宣稱完全零摩擦安裝。
- Windows 安裝包必須在 Windows x64 建置，macOS App 必須在 Mac 上建置；每個平台與架構都要實機驗證，不可用另一平台的建置結果替代。

## 13. 驗收標準

### 安裝與啟動

- 標準 Windows 使用者與非管理員 Mac 使用者可完成安裝／首次啟動。
- 重新登入與重新開機後，背景程式不會自動啟動；使用者手動開啟 App 後功能正常。
- 不出現命令提示字元視窗。
- 重複啟動不產生第二份 worker。
- 新版啟動與解除安裝都會清除舊預覽版登入自動啟動設定。
- macOS App 在 Apple Silicon 上通過 codesign、Gatekeeper 與 notarization 驗證；測試版則必須清楚標示尚未公證。

### 功能

- 至少以公開短片、1080p 影片、長影片、中文影片與英文影片各一支驗證解析。
- MP4、MP3 與逐字稿都需驗證檔案可正常開啟。
- 每項完成結果的「開啟資料夾」按鈕需直接開啟該工作成品所在資料夾，且本機
  API 只能接受已登記的完成檔案，不得接受任意路徑。
- 網路中斷、磁碟不足、影片不可用與工具更新失敗都有明確訊息。
- 程式重啟後已完成紀錄仍存在，未完成工作不會永久卡在 running。

### 更新

- 可從前一個正式版自動升級。
- 更新期間不破壞設定、模型、歷史紀錄與成品。
- 模擬損毀下載、錯誤簽章與新版啟動失敗時，系統拒絕更新或自動回復。
- 離線時維持原版本正常工作，不反覆彈出錯誤。

### 安全與隱私

- 區域網路其他裝置無法連入本機 API。
- 惡意網站不能直接建立 localhost 下載工作。
- 日誌與錯誤回報不包含 Cookie。
- 安裝包中不包含開發者或使用者的 YouTube Cookie。

## 14. 實作階段

### Phase 0：現有程式整理

- 修正逐字稿卡片 DOM id。
- 移除雲端 Cookie 打包與不正確的隱私文字。
- 將長工作從 request 內移到本機 queue。
- 新增測試與 README。

### Phase 1：本機桌面核心

- SQLite job store。
- Background worker。
- Windows launcher／tray 與 macOS menu bar／Login Item。
- Localhost 安全層與本機下載資料夾。

### Phase 2：Windows 與 macOS 打包

- Windows PyInstaller onedir 與 Inno Setup current-user installer。
- macOS Apple Silicon `.app`／`.dmg`、codesign、hardened runtime 與 notarization 流程。
- 內附工具、授權文件與解除安裝。
- Windows 10／11 與 Apple M2 Pro 實機驗收。

### Phase 3：自動更新

- GitHub Releases 發布流程。
- Signed manifest、staging、健康檢查與 rollback。
- yt-dlp 獨立更新與核准版本控制。

### Phase 4：發布品質

- 圖示、關於頁、版本資訊與授權清單。
- SmartScreen／程式碼簽章策略。
- 錯誤診斷匯出、隱私檢查與正式版驗收。

## 15. 完成定義

只有同時滿足以下條件，才可稱為「使用者安裝一次，以後直接開啟即可使用」：

- 乾淨 Windows 電腦或 Mac 不需預裝開發工具即可安裝。
- 手動開啟時不出現終端機視窗，重新開機後不會自行啟動。
- 一般公開影片可在目標測試集完成實際下載。
- MP3 與逐字稿在支援規格上完成端到端測試。
- 更新、回復、解除安裝與隱私邊界都有實測證據。

## 參考依據

- [PyInstaller：封裝 Python 與依賴](https://pyinstaller.org/en/stable/operating-mode.html)
- [Inno Setup：自動更新安裝方式](https://jrsoftware.org/ishelp/topic_technotes.htm)
- [GitHub Releases：發布檔案與配額](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [yt-dlp：更新頻道與回復版本](https://github.com/yt-dlp/yt-dlp/blob/master/README.md)
- [yt-dlp：瀏覽器 Cookie 注意事項](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [faster-whisper：CPU INT8 參考數據](https://github.com/SYSTRAN/faster-whisper)
- [Python sqlite3：免獨立伺服器的磁碟資料庫](https://docs.python.org/3/library/sqlite3.html)
- [FFmpeg：散布與授權要求](https://ffmpeg.org/legal.html)
- [Apple：macOS 軟體公證](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)
- [PyInstaller：macOS 簽章與 Apple Silicon](https://pyinstaller.org/en/stable/feature-notes.html)
- [whisper.cpp：Apple Silicon Metal 後端](https://github.com/ggml-org/whisper.cpp)
