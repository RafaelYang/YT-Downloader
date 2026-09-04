/**
 * YT Downloader by 學人新創 — 前端邏輯（混合架構 v2）
 * 流程：解析影片 → 使用者自由選擇下載 MP4 / MP3 / 逐字稿
 */

// ── DOM 元素 ──
const urlInput      = document.getElementById('url-input');
const pasteBtn      = document.getElementById('paste-btn');
const resolveBtn    = document.getElementById('resolve-btn');
const errorMsg      = document.getElementById('error-msg');
const videoInfo     = document.getElementById('video-info');
const actionSection = document.getElementById('action-section');
const qualityTrigger = document.getElementById('quality-trigger');
const qualityTriggerLabel = document.getElementById('quality-trigger-label');
const qualityTriggerSize = document.getElementById('quality-trigger-size');
const qualityDialog = document.getElementById('quality-dialog');
const qualityDialogClose = document.getElementById('quality-dialog-close');
const qualityDialogBackdrop = qualityDialog.querySelector('.quality-dialog-backdrop');
const qualityOptions = document.getElementById('quality-options');
const videoPreviewPanel = document.getElementById('video-preview-panel');
const videoPreview = document.getElementById('video-preview');

// 目前的 job_id（解析後取得）
let currentJobId = null;
let availableQualities = [];
let selectedQualityHeight = '';
const activeTasks = new Set();

// ── 解析影片 ──
async function resolveVideo() {
    if (activeTasks.size > 0) {
        showError('目前仍有工作處理中，完成後再切換影片');
        return;
    }

    const url = urlInput.value.trim();
    if (!url) {
        showError('請貼上 YouTube 影片網址');
        return;
    }

    // 隱藏之前的結果
    errorMsg.style.display = 'none';
    videoInfo.style.display = 'none';
    actionSection.style.display = 'none';
    setResolveLoading(true);

    try {
        const res = await fetch('/api/resolve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });

        const data = await res.json();

        if (!res.ok) {
            showError(data.detail || '解析失敗');
            return;
        }

        // 存儲 job_id
        currentJobId = data.job_id;

        // 顯示影片資訊
        document.getElementById('video-thumb').src = data.thumbnail || '';
        document.getElementById('video-title').textContent = data.title;
        document.getElementById('video-duration').textContent =
            `⏱ ${formatDuration(data.duration)}`;
        document.getElementById('video-quality').textContent =
            `📺 ${data.best_quality || '未知'}`;

        videoInfo.style.display = 'flex';

        // 重置所有卡片狀態
        resetAllCards();
        populateQualityOptions(data.qualities || []);

        // 顯示功能區
        actionSection.style.display = 'block';

    } catch (err) {
        showError('網路錯誤，請稍後重試');
        console.error(err);
    } finally {
        setResolveLoading(false);
    }
}


// ── 開始某項任務（mp4 / mp3 / transcript）──
function startTask(type) {
    if (!currentJobId) return;

    const btn = document.getElementById(`btn-${type}`);
    const progressEl = document.getElementById(`progress-${type}`);
    const fillEl = document.getElementById(`fill-${type}`);
    const textEl = document.getElementById(`text-${type}`);
    const dlEl = document.getElementById(`dl-${type}`);
    const resultActionsEl = document.getElementById(`result-actions-${type}`);
    const openFolderEl = document.getElementById(`open-folder-${type}`);
    const sizeEl = document.getElementById(`size-${type}`);
    activeTasks.add(type);
    if (type === 'mp4') {
        closeQualityDialog(false);
        qualityTrigger.disabled = true;
    }

    // 設定按鈕為 loading 狀態
    btn.disabled = true;
    btn.querySelector('.btn-action-text').style.display = 'none';
    btn.querySelector('.btn-action-loading').style.display = 'inline-flex';

    // 顯示進度條
    progressEl.style.display = 'block';
    resultActionsEl.style.display = 'none';
    openFolderEl.style.display = 'none';
    sizeEl.textContent = '';
    fillEl.style.width = '0%';

    // API 路徑
    let apiPath = `/api/process-${type}/${currentJobId}`;
    if (type === 'mp4' && selectedQualityHeight) {
        apiPath += `?quality=${encodeURIComponent(selectedQualityHeight)}`;
    }

    // 開始 SSE 連線
    const eventSource = new EventSource(apiPath);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.step === 'error') {
            // 錯誤處理
            eventSource.close();
            textEl.textContent = data.message;
            textEl.style.color = 'var(--accent-light)';
            fillEl.style.width = '0%';
            fillEl.style.background = 'var(--accent)';

            // 恢復按鈕
            btn.disabled = false;
            btn.querySelector('.btn-action-text').style.display = 'inline';
            btn.querySelector('.btn-action-loading').style.display = 'none';
            finishTask(type);
            return;
        }

        // 更新進度
        const progress = data.progress || 0;
        fillEl.style.width = `${progress}%`;
        textEl.textContent = data.message || '';
        textEl.style.color = '';

        if (data.step === 'done') {
            eventSource.close();

            // 隱藏進度，顯示下載按鈕
            progressEl.style.display = 'none';
            dlEl.href = data.download_url;
            resultActionsEl.style.display = 'flex';
            openFolderEl.style.display = data.saved_to ? 'inline-flex' : 'none';
            dlEl.textContent = data.saved_to ? '📥 另存一份' : '📥 儲存檔案';
            sizeEl.textContent = data.saved_to
                ? `${data.filesize || ''} · 已存入 ${data.saved_to}`
                : (data.filesize || '');

            // 處理逐字稿預覽
            if (type === 'transcript' && data.preview) {
                const previewEl = document.getElementById('preview-transcript');
                previewEl.textContent = data.preview;
                previewEl.style.display = 'block';
            }

            if (type === 'mp4' && data.preview_url) {
                videoPreview.src = data.preview_url;
                videoPreviewPanel.style.display = 'block';
                videoPreview.load();
            }

            // 恢復按鈕（改為「重新下載」狀態）
            btn.disabled = false;
            btn.querySelector('.btn-action-text').textContent = '🔄 重新';
            btn.querySelector('.btn-action-text').style.display = 'inline';
            btn.querySelector('.btn-action-loading').style.display = 'none';

            // 高亮卡片
            document.getElementById(`card-${type}`).classList.add('done');
            finishTask(type);
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        textEl.textContent = '❌ 連線中斷，請重試';
        textEl.style.color = 'var(--accent-light)';

        btn.disabled = false;
        btn.querySelector('.btn-action-text').style.display = 'inline';
        btn.querySelector('.btn-action-loading').style.display = 'none';
        finishTask(type);
    };
}

// 為了讓 HTML onclick 能呼叫
window.startTask = startTask;


// ── 開啟完成檔案所在資料夾 ──
async function openOutputFolder(type) {
    if (!currentJobId) return;

    const btn = document.getElementById(`open-folder-${type}`);
    const originalText = '📂 開啟資料夾';
    btn.disabled = true;
    btn.textContent = '📂 開啟中...';

    try {
        const response = await fetch(`/api/open-folder/${currentJobId}/${type}`, {
            method: 'POST',
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || '無法開啟資料夾');
        }
        btn.textContent = '✅ 已開啟';
    } catch (error) {
        btn.textContent = '❌ 開啟失敗';
        console.error(error);
    } finally {
        window.setTimeout(() => {
            btn.disabled = false;
            btn.textContent = originalText;
        }, 1400);
    }
}


window.openOutputFolder = openOutputFolder;


function finishTask(type) {
    activeTasks.delete(type);
    if (type === 'mp4') {
        qualityTrigger.disabled = availableQualities.length === 0;
    }
}


function populateQualityOptions(qualities) {
    closeQualityDialog(false);
    availableQualities = qualities;
    selectedQualityHeight = qualities.length > 0 ? String(qualities[0].height) : '';
    qualityOptions.replaceChildren();

    qualities.forEach((quality, index) => {
        const height = String(quality.height);
        const option = document.createElement('button');
        option.className = 'quality-option';
        option.id = `quality-option-${height}`;
        option.type = 'button';
        option.setAttribute('role', 'option');
        option.dataset.qualityHeight = height;
        option.setAttribute('aria-selected', height === selectedQualityHeight ? 'true' : 'false');

        const copy = document.createElement('span');
        copy.className = 'quality-option-copy';

        const title = document.createElement('strong');
        title.textContent = quality.label;

        const detail = document.createElement('small');
        detail.textContent = index === 0 ? '最高畫質' : '影片畫質';

        const size = document.createElement('span');
        size.className = 'quality-option-size';
        size.textContent = `預估 ${quality.estimated_size}`;

        const check = document.createElement('span');
        check.className = 'quality-option-check';
        check.setAttribute('aria-hidden', 'true');
        check.textContent = '✓';

        copy.append(title, detail);
        option.append(copy, size, check);
        option.addEventListener('click', () => selectQuality(height));
        qualityOptions.appendChild(option);
    });

    const mp4Button = document.getElementById('btn-mp4');
    if (qualities.length === 0) {
        qualityTriggerLabel.textContent = '沒有可用的影片畫質';
        qualityTriggerSize.textContent = '—';
        qualityTrigger.disabled = true;
        mp4Button.disabled = true;
        return;
    }

    qualityTrigger.disabled = false;
    mp4Button.disabled = false;
    updateQualitySelection();
}


function selectQuality(height) {
    selectedQualityHeight = height;
    updateQualitySelection();
    closeQualityDialog(true);
}


function updateQualitySelection() {
    const selected = availableQualities.find(
        (quality) => String(quality.height) === selectedQualityHeight,
    );
    if (!selected) return;

    qualityTriggerLabel.textContent = selected.label;
    qualityTriggerSize.textContent = `預估 ${selected.estimated_size}`;
    qualityOptions.querySelectorAll('[role="option"]').forEach((option) => {
        option.setAttribute(
            'aria-selected',
            option.dataset.qualityHeight === selectedQualityHeight ? 'true' : 'false',
        );
    });
}


function openQualityDialog() {
    if (qualityTrigger.disabled || availableQualities.length === 0) return;

    qualityDialog.hidden = false;
    qualityTrigger.setAttribute('aria-expanded', 'true');
    document.body.classList.add('quality-dialog-open');
    window.requestAnimationFrame(() => {
        const selectedOption = qualityOptions.querySelector('[aria-selected="true"]');
        (selectedOption || qualityDialogClose).focus();
    });
}


function closeQualityDialog(restoreFocus = true) {
    if (qualityDialog.hidden) return;

    qualityDialog.hidden = true;
    qualityTrigger.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('quality-dialog-open');
    if (restoreFocus && !qualityTrigger.disabled) {
        qualityTrigger.focus();
    }
}


function moveQualityFocus(direction) {
    const options = Array.from(qualityOptions.querySelectorAll('[role="option"]'));
    if (options.length === 0) return;

    const currentIndex = options.indexOf(document.activeElement);
    const nextIndex = currentIndex < 0
        ? 0
        : (currentIndex + direction + options.length) % options.length;
    options[nextIndex].focus();
}


function resetAllCards() {
    closeQualityDialog(false);
    videoPreview.pause();
    videoPreview.removeAttribute('src');
    videoPreview.load();
    videoPreviewPanel.style.display = 'none';

    ['mp4', 'mp3', 'transcript'].forEach(type => {
        const btn = document.getElementById(`btn-${type}`);
        const progressEl = document.getElementById(`progress-${type}`);
        const dlEl = document.getElementById(`dl-${type}`);
        const resultActionsEl = document.getElementById(`result-actions-${type}`);
        const openFolderEl = document.getElementById(`open-folder-${type}`);
        const sizeEl = document.getElementById(`size-${type}`);
        const card = document.getElementById(`card-${type}`);

        btn.disabled = false;
        // 恢復按鈕原始文字
        const origTexts = { mp4: '📥 下載', mp3: '📥 下載', transcript: '🧠 產生' };
        btn.querySelector('.btn-action-text').textContent = origTexts[type];
        btn.querySelector('.btn-action-text').style.display = 'inline';
        btn.querySelector('.btn-action-loading').style.display = 'none';

        progressEl.style.display = 'none';
        resultActionsEl.style.display = 'none';
        dlEl.textContent = '📥 儲存檔案';
        openFolderEl.style.display = 'none';
        openFolderEl.disabled = false;
        openFolderEl.textContent = '📂 開啟資料夾';
        sizeEl.textContent = '';
        card.classList.remove('done');
    });

    // 隱藏逐字稿預覽
    const previewEl = document.getElementById('preview-transcript');
    if (previewEl) {
        previewEl.style.display = 'none';
        previewEl.textContent = '';
    }
}


// ── 工具函式 ──
function showError(msg) {
    errorMsg.textContent = `❌ 錯誤：${msg}`;
    errorMsg.style.display = 'block';
}


function setResolveLoading(loading) {
    resolveBtn.disabled = loading;
    resolveBtn.querySelector('.btn-text').style.display = loading ? 'none' : 'inline';
    resolveBtn.querySelector('.btn-loading').style.display = loading ? 'inline-flex' : 'none';
}


function formatDuration(sec) {
    if (!sec) return '—';
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
}


// ── 貼上功能 ──
pasteBtn.addEventListener('click', async () => {
    try {
        const text = await navigator.clipboard.readText();
        urlInput.value = text;
        urlInput.focus();
    } catch {
        urlInput.focus();
        document.execCommand('paste');
    }
});


// ── 事件綁定 ──
resolveBtn.addEventListener('click', resolveVideo);

qualityTrigger.addEventListener('click', openQualityDialog);
qualityTrigger.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        openQualityDialog();
    }
});

qualityDialogClose.addEventListener('click', () => closeQualityDialog(true));
qualityDialogBackdrop.addEventListener('click', () => closeQualityDialog(true));

qualityDialog.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        event.preventDefault();
        closeQualityDialog(true);
        return;
    }
    if (event.key === 'ArrowDown') {
        event.preventDefault();
        moveQualityFocus(1);
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        moveQualityFocus(-1);
    } else if (event.key === 'Home') {
        event.preventDefault();
        qualityOptions.querySelector('[role="option"]')?.focus();
    } else if (event.key === 'End') {
        event.preventDefault();
        const options = qualityOptions.querySelectorAll('[role="option"]');
        options[options.length - 1]?.focus();
    }
});

urlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !resolveBtn.disabled) {
        resolveVideo();
    }
});
