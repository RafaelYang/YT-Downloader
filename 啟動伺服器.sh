#!/bin/bash
# ═══════════════════════════════════════════════
# YT Downloader by 學人新創 一鍵啟動腳本
# 啟動本機伺服器 + Cloudflare 隧道（產生公開網址）
# ═══════════════════════════════════════════════

# 取得腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "🎬 ═══════════════════════════════════════"
echo "   YT Downloader by 學人新創 啟動中..."
echo "═══════════════════════════════════════════"
echo ""

# 檢查 Python 虛擬環境
if [ ! -d ".venv" ]; then
    echo "⚙️  首次執行，建立虛擬環境中..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    echo ""
fi

# 檢查 cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "⚙️  安裝 Cloudflare Tunnel 工具..."
    brew install cloudflared
    echo ""
fi

# 先關閉可能殘留的舊進程
pkill -f "uvicorn.*8080" 2>/dev/null
pkill -f "cloudflared.*tunnel" 2>/dev/null
sleep 1

# 啟動 Python 伺服器（背景執行）
echo "🚀 啟動本機伺服器..."
.venv/bin/python app.py &
SERVER_PID=$!
sleep 2

# 確認伺服器啟動成功
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ 伺服器啟動失敗！"
    exit 1
fi

echo "✅ 伺服器已啟動 (PID: $SERVER_PID)"
echo ""

# 啟動 Cloudflare 隧道
echo "🌐 建立公開隧道中..."
echo ""

# cloudflared 會在 stderr 輸出隧道 URL
cloudflared tunnel --url http://localhost:8000 2>&1 | while IFS= read -r line; do
    # 抓取隧道 URL
    if echo "$line" | grep -q "https://.*trycloudflare.com"; then
        TUNNEL_URL=$(echo "$line" | grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
        if [ -n "$TUNNEL_URL" ]; then
            echo ""
            echo "═══════════════════════════════════════════"
            echo "🎉 準備好了！把這個網址傳給對方："
            echo ""
            echo "   👉 $TUNNEL_URL"
            echo ""
            echo "═══════════════════════════════════════════"
            echo ""
            echo "📌 注意事項："
            echo "   • 對方用手機或電腦的瀏覽器打開即可"
            echo "   • 你的電腦必須保持開啟（關掉此視窗就停止）"
            echo "   • 按 Ctrl+C 停止服務"
            echo ""
        fi
    fi
done

# 清理
echo ""
echo "🛑 正在關閉服務..."
kill $SERVER_PID 2>/dev/null
echo "👋 已停止！"
