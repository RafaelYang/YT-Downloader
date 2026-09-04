FROM python:3.11-slim

# 安裝 ffmpeg（轉檔用）和 Node.js（yt-dlp 的 n-challenge 解碼需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先安裝 CPU 版本的 PyTorch，避免預設安裝 CUDA 版本的巨大 PyTorch 庫 (超過 2GB)
# 這可以大幅縮短 Cloud Build 部署時間與映像檔大小
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 安裝其餘 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 確保 yt-dlp 是最新版（YouTube 經常更新反爬蟲機制）
RUN pip install --no-cache-dir --upgrade yt-dlp

# 預先下載 Whisper small 模型（避免每次冷啟動都要重新下載）
RUN python -c "import whisper; whisper.load_model('small', device='cpu')"

# 複製應用程式碼
COPY app.py .
COPY static/ static/

# Cloud Run 會透過 PORT 環境變數指定 port
ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
