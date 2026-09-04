# YT Downloader — Windows 部署指令

> **這份文件是給 AI 助手閱讀並執行的安裝指令。**
> 請依照以下步驟，在這台 Windows 電腦上完成 YT Downloader 的部署。

---

## 專案說明

這是一個 YouTube 影片下載工具，提供：
- 📥 MP4 影片下載
- 🎵 MP3 音檔轉換
- 📝 AI 語音逐字稿（Whisper）

架構：FastAPI 後端 + 純 HTML/CSS/JS 前端，需透過 Tailscale Funnel 對外提供固定 HTTPS 網址。

---

## 第一階段：環境檢查與安裝

### 1.1 檢查 Python

在終端機（PowerShell 或 CMD）執行：

```powershell
python --version
```

- 如果顯示 Python 3.10 以上 → 繼續下一步
- 如果找不到 Python → 請到 https://www.python.org/downloads/ 下載安裝
  - **安裝時務必勾選 `Add Python to PATH`**
  - 安裝完後重開終端機再確認

### 1.2 檢查 ffmpeg

```powershell
ffmpeg -version
```

- 如果顯示版本資訊 → 繼續下一步
- 如果找不到 ffmpeg → 執行以下安裝步驟：

**方法 A（推薦，用 winget）：**
```powershell
winget install Gyan.FFmpeg
```

**方法 B（手動安裝）：**
1. 到 https://github.com/BtbN/FFmpeg-Builds/releases 下載 `ffmpeg-master-latest-win64-gpl.zip`
2. 解壓縮到 `C:\ffmpeg`
3. 將 `C:\ffmpeg\bin` 加入系統環境變數 PATH
4. 重開終端機確認 `ffmpeg -version` 可執行

### 1.3 檢查 Tailscale

```powershell
tailscale version
```

- 如果顯示版本 → 繼續下一步
- 如果找不到 → 到 https://tailscale.com/download/windows 下載安裝
  - 安裝後用 Google 帳號登入
  - 確認系統列有 Tailscale 圖示且顯示「Connected」

---

## 第二階段：部署專案

### 2.1 進入專案目錄

```powershell
cd "這個檔案所在的資料夾路徑"
```

> 如果這個專案放在 `D:\YT-Downloader\`，就執行 `cd D:\YT-Downloader`

### 2.2 建立 Python 虛擬環境

```powershell
python -m venv .venv
```

### 2.3 啟動虛擬環境

```powershell
.venv\Scripts\activate
```

成功後命令列最前面會出現 `(.venv)`

### 2.4 安裝 Python 依賴

```powershell
pip install -r requirements.txt
pip install "yt-dlp[default]"
```

> 這會安裝 FastAPI、yt-dlp、Whisper 等所有需要的套件。
> Whisper 會自動下載 PyTorch，第一次安裝可能需要幾分鐘。

### 2.5 測試伺服器啟動

```powershell
python app.py
```

預期輸出：
```
🚀 YT 下載工具已啟動 — http://localhost:8000
```

在瀏覽器打開 `http://localhost:8000`，確認可以看到 YT Downloader 的網頁介面。

確認成功後按 `Ctrl+C` 先停止伺服器。

---

## 第三階段：設定固定網址（Tailscale Funnel）

### 3.1 啟用 HTTPS Funnel

**用系統管理員身分**開啟 PowerShell，執行：

```powershell
tailscale funnel 8000
```

- 第一次會問是否啟用 Funnel → 輸入 `yes` 或按確認
- 成功後會顯示固定網址，格式類似：

```
https://機器名稱.尾碼.ts.net/
|-- 你的 funnel is accessible from the internet: --|
```

**記下這個 `https://xxx.ts.net` 網址，這就是對外公開的永久固定網址。**

### 3.2 測試完整流程

1. 在一個終端機視窗啟動伺服器：
   ```powershell
   cd "專案目錄"
   .venv\Scripts\activate
   python app.py
   ```

2. 在另一個終端機視窗（管理員）啟動 Funnel：
   ```powershell
   tailscale funnel 8000
   ```

3. 用手機或另一台電腦的瀏覽器打開那個 `https://xxx.ts.net` 網址
4. 確認可以看到 YT Downloader 頁面
5. 貼一個 YouTube 網址測試解析和下載

---

## 第四階段：設定開機自動啟動

為了讓電腦重開機後自動執行，需要建立自動啟動。

### 4.1 確認 start.bat 內容

專案目錄裡應該已有 `start.bat`，確認內容如下：

```bat
@echo off
chcp 65001 >nul
title YT Downloader 伺服器

cd /d "%~dp0"

echo 啟動 YT Downloader...
start /b .venv\Scripts\python app.py
timeout /t 3 /nobreak >nul
tailscale funnel 8000
pause
```

如果沒有這個檔案，請建立它。

### 4.2 加入開機啟動

1. 按 `Win + R`，輸入 `shell:startup`，按 Enter
2. 這會打開「啟動」資料夾
3. 對 `start.bat` 按右鍵 →「建立捷徑」
4. 把捷徑拖到剛才打開的「啟動」資料夾裡

這樣電腦每次開機都會自動啟動 YT Downloader 並開啟 Funnel。

---

## 驗證清單

完成後請逐項確認：

- [ ] `python --version` 顯示 3.10+
- [ ] `ffmpeg -version` 正常執行
- [ ] `tailscale version` 正常執行且已登入
- [ ] `python app.py` 可啟動伺服器在 `localhost:8000`
- [ ] `tailscale funnel 8000` 顯示固定的 `https://xxx.ts.net` 網址
- [ ] 用手機瀏覽器打開該網址可正常使用
- [ ] 貼 YouTube 網址可正常解析和下載
- [ ] `start.bat` 捷徑已放入 `shell:startup` 資料夾

---

## 常見問題

### Q: pip install 時出現紅色錯誤
可能是 Python 版本太舊。確認用的是 Python 3.10 以上。

### Q: Whisper 下載很慢
第一次執行逐字稿時會自動下載 Whisper 模型（約 500MB），請耐心等待。

### Q: Tailscale Funnel 無法啟用
確保用「以系統管理員身分執行」的 PowerShell 來執行 `tailscale funnel`。

### Q: YouTube 影片解析失敗
執行 `pip install --upgrade yt-dlp` 更新 yt-dlp 到最新版。

### Q: 想更新 Cookie
將新的 Cookie 檔案（Netscape 格式）放到專案目錄，命名為 `youtube_cookies.txt`。
