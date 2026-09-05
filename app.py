"""
YT Downloader by 學人新創 — 網頁版（混合架構 v2）
功能：
  1. 解析 YouTube 影片網址 → 顯示影片資訊與可用畫質
  2. 依使用者選擇獨立下載 MP4 / MP3 / 產生 AI 逐字稿
技術：FastAPI + yt-dlp + ffmpeg + OpenAI Whisper
"""

import os
import re
import uuid
import json
import asyncio
import importlib.machinery
import importlib.util
import secrets
import shutil
import subprocess
import sys
import threading
import traceback
import types
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

import yt_dlp

from desktop_config import APP_VERSION, PRODUCT_NAME, ensure_desktop_directories, resource_dir
from desktop_platform import open_folder
from translation_model_manager import ensure_translation_model
from whisper_model_manager import ensure_whisper_model

# ── 全域變數 ──
app = FastAPI(title=PRODUCT_NAME, version=APP_VERSION)
resolved_jobs: dict = {}   # 快取已解析的影片資訊 { job_id: {...} }
whisper_model = None
translation_model = None
translation_tokenizer = None
traditional_chinese_converter = None
output_directory_lock = threading.Lock()
whisper_model_lock = threading.Lock()
translation_model_lock = threading.Lock()
traditional_chinese_lock = threading.Lock()

BASE_DIR = Path(__file__).resolve().parent
RESOURCE_DIR = resource_dir()


def load_packaged_pot_plugin(plugin_root: Path) -> bool:
    """Load the physical HTTP provider source that PyInstaller cannot discover."""
    package_paths = {
        'yt_dlp_plugins': plugin_root / 'yt_dlp_plugins',
        'yt_dlp_plugins.extractor': plugin_root / 'yt_dlp_plugins' / 'extractor',
    }
    for name, path in package_paths.items():
        if name in sys.modules:
            continue
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        module.__package__ = name
        module.__spec__ = importlib.machinery.ModuleSpec(
            name,
            loader=None,
            is_package=True,
        )
        sys.modules[name] = module

    modules = [
        'getpot_bgutil',
        'getpot_bgutil_http',
    ]
    for basename in modules:
        module_name = f'yt_dlp_plugins.extractor.{basename}'
        if module_name in sys.modules:
            continue
        filepath = package_paths['yt_dlp_plugins.extractor'] / f'{basename}.py'
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return False
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

    # The bundled provider has already registered itself. Prevent yt-dlp's
    # filesystem plugin pass from importing the same module a second time.
    from yt_dlp.globals import all_plugins_loaded

    all_plugins_loaded.value = True
    return True


def configure_ytdlp_plugin_path() -> tuple[Path | None, bool]:
    """Register the physical provider plugin directory inside source or App bundles."""
    candidates = [
        RESOURCE_DIR / 'pot-provider' / 'plugin',
        BASE_DIR / 'vendor' / 'bgutil-ytdlp-pot-provider' / 'plugin',
    ]
    plugin_root = next(
        (path for path in candidates if (path / 'yt_dlp_plugins').is_dir()),
        None,
    )
    if plugin_root is None:
        return None, False

    if getattr(sys, 'frozen', False):
        return plugin_root, load_packaged_pot_plugin(plugin_root)

    from yt_dlp.globals import plugin_dirs

    root_value = str(plugin_root)
    if root_value not in plugin_dirs.value:
        plugin_dirs.value.insert(0, root_value)
    return plugin_root, True


POT_PLUGIN_DIR, POT_PLUGIN_READY = configure_ytdlp_plugin_path()

# Cloud Run 環境偵測：K_SERVICE 是 Cloud Run 自動注入的環境變數
IS_CLOUD = bool(os.environ.get('K_SERVICE'))
IS_DESKTOP = os.environ.get('YT_DESKTOP') == '1'
LOCAL_SESSION_TOKEN = os.environ.get('YT_LOCAL_TOKEN', '')
LOCAL_SESSION_COOKIE = 'yt_downloader_session'

if IS_DESKTOP:
    DESKTOP_PATHS = ensure_desktop_directories()
    DOWNLOAD_DIR = DESKTOP_PATHS['jobs']
    MODEL_DIR = DESKTOP_PATHS['models']
else:
    DESKTOP_PATHS = {}
    # Cloud Run 的檔案系統是唯讀的，只有 /tmp 可寫入。
    DOWNLOAD_DIR = Path('/tmp/yt-downloads') if IS_CLOUD else BASE_DIR / 'downloads'
    MODEL_DIR = None

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_YOUTUBE_HOSTS = {
    'youtube.com',
    'www.youtube.com',
    'm.youtube.com',
    'music.youtube.com',
    'youtu.be',
    'www.youtu.be',
}
OUTPUT_KINDS = {'mp4', 'mp3', 'transcript'}
TRANSCRIPT_LANGUAGES = {'zh-TW', 'en'}
WHISPER_MODEL_NAME = 'turbo'


def find_media_tool(name: str) -> str:
    """Prefer the packaged tool, then fall back to the developer machine PATH."""
    filenames = [f'{name}.exe', name] if sys.platform.startswith('win') else [name]
    vendor_platform = (
        'windows-x64'
        if sys.platform.startswith('win')
        else 'macos-arm64' if sys.platform == 'darwin' else None
    )
    candidates = []
    for filename in filenames:
        candidates.append(RESOURCE_DIR / 'tools' / filename)
        if vendor_platform:
            candidates.append(BASE_DIR / 'vendor' / vendor_platform / filename)
        candidates.append(Path(sys.executable).resolve().parent / 'tools' / filename)
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return next((path for filename in filenames if (path := shutil.which(filename))), name)


FFMPEG_PATH = find_media_tool('ffmpeg')
FFPROBE_PATH = find_media_tool('ffprobe')
NODE_PATH = find_media_tool('node')
POT_PROVIDER_URL = os.environ.get('YT_POT_PROVIDER_URL', '').rstrip('/')

if IS_DESKTOP and Path(FFMPEG_PATH).is_file():
    # OpenAI Whisper invokes `ffmpeg` by name even when the input is already WAV.
    # Expose the trusted bundled tools directory so packaged Windows/macOS builds
    # do not depend on a separately installed FFmpeg.
    tool_directory = str(Path(FFMPEG_PATH).resolve().parent)
    existing_path = os.environ.get('PATH', '')
    if tool_directory not in existing_path.split(os.pathsep):
        os.environ['PATH'] = (
            f'{tool_directory}{os.pathsep}{existing_path}'
            if existing_path
            else tool_directory
        )


# ── Pydantic Models ──
class ResolveRequest(BaseModel):
    url: str


# ── 工具函式 ──
def safe_filename(s: str, maxlen: int = 60) -> str:
    """移除檔名中的非法字元"""
    s = re.sub(r'[\\/:*?"<>|]+', '_', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s*_\s*', '_', s)
    return s[:maxlen]


def output_stem(
    title: str,
    kind: str,
    quality: int | None = None,
    transcript_language: str | None = None,
) -> str:
    """Build a user-facing filename stem as title_kind[_quality]."""
    labels = {
        'mp4': '影片',
        'mp3': '音檔',
        'transcript': '逐字稿',
    }
    clean_title = safe_filename(title) or 'untitled'
    parts = [clean_title, labels[kind]]
    if kind == 'mp4' and quality is not None:
        parts.append(f'{quality}p')
    if kind == 'transcript' and transcript_language == 'zh-TW':
        parts.append('繁中')
    elif kind == 'transcript' and transcript_language == 'en':
        parts.append('英文雙語')
    return '_'.join(parts)


def validate_youtube_url(url: str) -> str:
    """Validate and normalize a supported public YouTube HTTPS URL."""
    value = url.strip()
    if not value:
        raise ValueError('請輸入 YouTube 網址')

    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError('YouTube 網址的連接埠格式不正確') from exc
    if (
        parsed.scheme.lower() != 'https'
        or parsed.hostname is None
        or parsed.hostname.lower() not in ALLOWED_YOUTUBE_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ValueError('只支援 youtube.com 或 youtu.be 的 HTTPS 影片網址')
    return value


def format_bytes(size) -> str:
    """格式化檔案大小"""
    if not size:
        return '—'
    size = float(size)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def estimate_format_size(format_info: dict, duration: float) -> int | None:
    """Estimate a single stream size from yt-dlp metadata."""
    declared = format_info.get('filesize') or format_info.get('filesize_approx')
    if declared:
        return int(declared)

    bitrate = format_info.get('tbr')
    if bitrate and duration:
        return int(float(bitrate) * 1000 / 8 * float(duration))
    return None


def heuristic_video_bitrate(height: int) -> int:
    """Return a conservative kbps fallback when YouTube omits stream bitrate."""
    for maximum_height, bitrate in (
        (144, 180),
        (240, 350),
        (360, 750),
        (480, 1200),
        (720, 2800),
        (1080, 5000),
        (1440, 9000),
        (2160, 18000),
    ):
        if height <= maximum_height:
            return bitrate
    return 28000


def build_quality_options(formats: list[dict], duration: float) -> list[dict]:
    """Build descending video-quality choices with combined audio estimates."""
    audio_formats = [
        item
        for item in formats
        if item.get('vcodec', 'none') == 'none'
        and item.get('acodec', 'none') != 'none'
    ]
    preferred_audio_formats = [
        item
        for item in audio_formats
        if item.get('ext') == 'm4a'
        and str(item.get('acodec', '')).lower().startswith('mp4a')
    ]
    if not preferred_audio_formats:
        preferred_audio_formats = [
            item for item in audio_formats if item.get('ext') == 'm4a'
        ]
    preferred_audio = max(
        preferred_audio_formats or audio_formats,
        key=lambda item: float(item.get('abr') or item.get('tbr') or 0),
        default=None,
    )
    audio_size = (
        estimate_format_size(preferred_audio, duration)
        if preferred_audio is not None
        else None
    )
    if audio_size is None and duration:
        audio_size = int(128 * 1000 / 8 * float(duration))

    best_by_height: dict[int, tuple[tuple, dict]] = {}
    for item in formats:
        if item.get('vcodec', 'none') == 'none':
            continue
        height = int(item.get('height') or 0)
        if height <= 0:
            continue

        stream_size = estimate_format_size(item, duration)
        if stream_size is None and duration:
            stream_size = int(
                heuristic_video_bitrate(height) * 1000 / 8 * float(duration)
            )
        combined_size = stream_size
        if item.get('acodec', 'none') == 'none' and audio_size:
            combined_size = (combined_size or 0) + audio_size

        video_codec = str(item.get('vcodec', '')).lower()
        score = (
            video_codec.startswith(('avc1', 'h264')),
            item.get('ext') == 'mp4',
            float(item.get('fps') or 0),
            float(item.get('vbr') or item.get('tbr') or 0),
        )
        existing = best_by_height.get(height)
        if existing is None or score > existing[0]:
            best_by_height[height] = (
                score,
                {
                    'height': height,
                    'label': f'{height}p',
                    'estimated_size_bytes': combined_size,
                    'estimated_size': format_bytes(combined_size),
                },
            )

    return [
        best_by_height[height][1]
        for height in sorted(best_by_height, reverse=True)
    ]


def quality_format_selector(height: int) -> str:
    """Select the requested height and prefer QuickTime-compatible streams."""
    return (
        f'bestvideo[height={height}][vcodec^=avc1][ext=mp4]+'
        f'bestaudio[acodec^=mp4a][ext=m4a]/'
        f'bestvideo[height={height}][vcodec^=avc1]+'
        f'bestaudio[acodec^=mp4a]/'
        f'best[height={height}][vcodec^=avc1][acodec^=mp4a][ext=mp4]/'
        f'bestvideo[height={height}][ext=mp4]+bestaudio[ext=m4a]/'
        f'bestvideo[height={height}]+bestaudio/'
        f'best[height={height}][ext=mp4]/best[height={height}]'
    )


def probe_media_streams(filepath: Path) -> dict[str, dict]:
    """Read the first video and audio streams from a completed media file."""
    result = subprocess.run(
        [
            FFPROBE_PATH,
            '-v',
            'error',
            '-show_entries',
            'stream=codec_type,codec_name,pix_fmt,height',
            '-of',
            'json',
            str(filepath),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    streams = json.loads(result.stdout).get('streams', [])
    return {
        codec_type: next(
            (stream for stream in streams if stream.get('codec_type') == codec_type),
            {},
        )
        for codec_type in ('video', 'audio')
    }


def probe_video_height(filepath: Path) -> int:
    """Read the actual output height so a selected quality cannot be mislabeled."""
    video_stream = probe_media_streams(filepath)['video']
    if not video_stream.get('height'):
        raise RuntimeError('無法確認下載影片的實際畫質。')
    return int(video_stream['height'])


def is_playback_compatible(streams: dict[str, dict], filepath: Path) -> bool:
    """Return whether the file is a broadly compatible H.264/AAC MP4."""
    video = streams.get('video', {})
    audio = streams.get('audio', {})
    return (
        filepath.suffix.lower() == '.mp4'
        and video.get('codec_name') == 'h264'
        and video.get('pix_fmt') in {'yuv420p', 'yuvj420p'}
        and audio.get('codec_name') in {None, 'aac'}
    )


def ensure_playback_compatible(filepath: Path) -> tuple[Path, bool]:
    """Convert an incompatible download to an H.264/AAC MP4 atomically."""
    streams = probe_media_streams(filepath)
    if is_playback_compatible(streams, filepath):
        return filepath, False

    video = streams.get('video', {})
    audio = streams.get('audio', {})
    target = filepath.with_suffix('.mp4')
    temporary = filepath.parent / f'_{filepath.stem}.compatible.tmp.mp4'
    temporary.unlink(missing_ok=True)

    video_args = ['-c:v', 'copy']
    if not (
        video.get('codec_name') == 'h264'
        and video.get('pix_fmt') in {'yuv420p', 'yuvj420p'}
    ):
        video_args = [
            '-c:v',
            'libx264',
            '-preset',
            'veryfast',
            '-crf',
            '20',
            '-pix_fmt',
            'yuv420p',
        ]

    audio_args = ['-c:a', 'copy'] if audio.get('codec_name') == 'aac' else [
        '-c:a',
        'aac',
        '-b:a',
        '192k',
    ]

    try:
        subprocess.run(
            [
                FFMPEG_PATH,
                '-y',
                '-v',
                'error',
                '-i',
                str(filepath),
                '-map',
                '0:v:0',
                '-map',
                '0:a:0?',
                *video_args,
                *audio_args,
                '-movflags',
                '+faststart',
                str(temporary),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        converted_streams = probe_media_streams(temporary)
        if not is_playback_compatible(converted_streams, temporary):
            raise RuntimeError('轉換後的影片仍不是 H.264／AAC 相容格式。')

        if target != filepath:
            target.unlink(missing_ok=True)
        temporary.replace(target)
        if target != filepath:
            filepath.unlink(missing_ok=True)
        return target, True
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def registered_output_file(job_id: str, kind: str) -> Path:
    """Return only a completed output path previously registered for this job."""
    if not re.fullmatch(r'[0-9a-f]{8}', job_id) or kind not in OUTPUT_KINDS:
        raise HTTPException(404, '檔案不存在或已過期')

    job = resolved_jobs.get(job_id, {})
    registered = job.get('outputs', {}).get(kind)
    if not registered:
        raise HTTPException(404, '檔案不存在或已過期')
    filepath = Path(registered).resolve()
    if not filepath.is_file():
        raise HTTPException(404, '檔案不存在或已過期')
    return filepath


def create_timestamp_output_dir(
    output_root: Path,
    now: datetime | None = None,
    title: str | None = None,
) -> Path:
    """Create a title-and-minute output folder without reusing an existing one."""
    timestamp = (now or datetime.now()).strftime('%y%m%d_%H%M')
    safe_title = safe_filename(title or '') or 'untitled'
    folder_stem = f'{safe_title}_{timestamp}'
    counter = 1
    while True:
        suffix = '' if counter == 1 else f'_{counter}'
        candidate = output_root / f'{folder_stem}{suffix}'
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            counter += 1


def get_job_output_dir(job_id: str) -> Path:
    """Allocate one timestamp folder shared by all outputs for a resolved job."""
    with output_directory_lock:
        job = resolved_jobs[job_id]
        existing = job.get('output_dir')
        if existing:
            path = Path(existing)
            path.mkdir(parents=True, exist_ok=True)
            return path

        path = create_timestamp_output_dir(
            DESKTOP_PATHS['output'],
            title=str(job.get('title') or 'untitled'),
        )
        job['output_dir'] = str(path.resolve())
        return path


def publish_completed_file(job_id: str, kind: str, source: Path) -> tuple[Path, str | None]:
    """Move desktop output to Downloads and register the only downloadable path."""
    final_path = source
    saved_to = None
    if IS_DESKTOP:
        output_dir = get_job_output_dir(job_id)
        candidate = output_dir / source.name
        counter = 2
        while candidate.exists():
            candidate = output_dir / f"{source.stem} ({counter}){source.suffix}"
            counter += 1
        final_path = Path(shutil.move(str(source), str(candidate)))
        saved_to = f"下載項目/{output_dir.name}"

    resolved_jobs[job_id].setdefault('outputs', {})[kind] = str(final_path.resolve())
    return final_path, saved_to


def get_whisper_model():
    """延遲載入 Whisper 模型（Apple Silicon 用 MPS，雲端用 CPU）"""
    global whisper_model
    if whisper_model is not None:
        return whisper_model

    with whisper_model_lock:
        if whisper_model is not None:
            return whisper_model

        import whisper
        import torch

        # 雲端環境只能用 CPU；本機 Apple Silicon 用 MPS 加速
        if IS_CLOUD:
            device = "cpu"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        print(f"🧠 載入 Whisper 模型 ({WHISPER_MODEL_NAME})，裝置：{device}")

        if IS_DESKTOP and MODEL_DIR:
            model_url = whisper._MODELS[WHISPER_MODEL_NAME]
            ensure_whisper_model(WHISPER_MODEL_NAME, model_url, MODEL_DIR)
        kwargs = {'download_root': str(MODEL_DIR)} if MODEL_DIR else {}
        whisper_model = whisper.load_model(WHISPER_MODEL_NAME, device=device, **kwargs)
    return whisper_model


def get_translation_model():
    """Lazily load the pinned offline English-to-Chinese translation model."""
    global translation_model, translation_tokenizer
    if translation_model is not None and translation_tokenizer is not None:
        return translation_tokenizer, translation_model

    with translation_model_lock:
        if translation_model is not None and translation_tokenizer is not None:
            return translation_tokenizer, translation_model

        from transformers import MarianMTModel, MarianTokenizer

        if MODEL_DIR is None:
            raise RuntimeError('英中雙語逐字稿目前只支援桌面版')
        model_path = ensure_translation_model(MODEL_DIR)
        print(f"🌐 載入英中翻譯模型：{model_path.name}")
        translation_tokenizer = MarianTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
        )
        translation_model = MarianMTModel.from_pretrained(
            model_path,
            local_files_only=True,
        )
        translation_model.eval()
    return translation_tokenizer, translation_model


def to_traditional_chinese(text: str) -> str:
    """Convert Simplified or mixed Chinese text into Taiwan Traditional Chinese."""
    global traditional_chinese_converter
    with traditional_chinese_lock:
        if traditional_chinese_converter is None:
            from opencc import OpenCC

            traditional_chinese_converter = OpenCC('s2twp')
        converted = traditional_chinese_converter.convert(text)
        # OpenCC preserves the literary variant 「瞭」 in some perfect-aspect
        # phrases (for example 「解釋瞭」), which is unnatural in modern Taiwan
        # transcript prose. 「了」 is the appropriate neutral form here.
        return converted.replace('瞭', '了')


def translate_english_segments(texts: list[str]) -> list[str]:
    """Translate English segments locally, preserving one output per input."""
    if not texts:
        return []

    import torch

    tokenizer, model = get_translation_model()
    translations = []
    with torch.inference_mode():
        for start in range(0, len(texts), 8):
            batch_texts = texts[start:start + 8]
            tokens = tokenizer(
                batch_texts,
                return_tensors='pt',
                padding=True,
                truncation=True,
                max_length=512,
            )
            generated = model.generate(
                **tokens,
                max_new_tokens=256,
                num_beams=4,
            )
            simplified = tokenizer.batch_decode(generated, skip_special_tokens=True)
            translations.extend(to_traditional_chinese(text) for text in simplified)
    return translations


def normalize_transcript_segments(result: dict) -> list[dict]:
    """Return clean Whisper segments with stable timestamps."""
    segments = []
    for item in result.get('segments') or []:
        text = re.sub(r'\s+', ' ', str(item.get('text') or '')).strip()
        if not text:
            continue
        start = max(0.0, float(item.get('start') or 0.0))
        end = max(start, float(item.get('end') or start))
        segments.append({'start': start, 'end': end, 'text': text})

    fallback = re.sub(r'\s+', ' ', str(result.get('text') or '')).strip()
    if not segments and fallback:
        segments.append({'start': 0.0, 'end': 0.0, 'text': fallback})
    return segments


def transcript_timestamp(seconds: float) -> str:
    """Format a Whisper timestamp as MM:SS or HH:MM:SS."""
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f'{hours:02d}:{minutes:02d}:{secs:02d}'
    return f'{minutes:02d}:{secs:02d}'


def render_transcript(
    title: str,
    language: str,
    segments: list[dict],
    translations: list[str] | None = None,
) -> str:
    """Render timestamped Traditional-Chinese or bilingual transcript text."""
    if language not in TRANSCRIPT_LANGUAGES:
        raise ValueError('不支援的逐字稿語言')
    translations = translations or []
    if language == 'en' and len(translations) != len(segments):
        raise ValueError('英中翻譯段落數量不一致')

    mode_label = '繁體中文分段' if language == 'zh-TW' else 'English＋繁體中文分段'
    lines = [f'📌 {title}', f'語言：{mode_label}', f'模型：Whisper {WHISPER_MODEL_NAME}', '=' * 50, '']
    for index, segment in enumerate(segments):
        timestamp = (
            f"[{transcript_timestamp(segment['start'])} → "
            f"{transcript_timestamp(segment['end'])}]"
        )
        lines.append(timestamp)
        if language == 'zh-TW':
            lines.append(to_traditional_chinese(segment['text']))
        else:
            lines.append(f"英文：{segment['text']}")
            lines.append(f"中文：{translations[index]}")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def get_yt_dlp_base_opts() -> dict:
    """取得不含登入憑證的 yt-dlp 基本選項。"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {'player_client': ['web_creator', 'android_creator', 'mweb']},
        },
        'ffmpeg_location': str(Path(FFMPEG_PATH).parent),
    }
    if Path(NODE_PATH).is_file():
        opts['js_runtimes'] = {'node': {'path': NODE_PATH}}
    return opts


def get_pot_provider_opts() -> dict | None:
    """Use the bundled local PO-token provider for downloadable mweb formats."""
    if not POT_PROVIDER_URL:
        return None
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'noplaylist': True,
        'extractor_args': {
            'youtube': {'player_client': ['mweb']},
            'youtubepot-bgutilhttp': {'base_url': [POT_PROVIDER_URL]},
        },
        'ffmpeg_location': str(Path(FFMPEG_PATH).parent),
    }
    if Path(NODE_PATH).is_file():
        opts['js_runtimes'] = {'node': {'path': NODE_PATH}}
    return opts


def sse_event(data: dict) -> str:
    """產生 SSE 格式的事件字串"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def get_opts_for_strategy(strategy: str) -> dict:
    """根據解析時成功的策略，產生對應的 yt-dlp 選項"""
    base = {'quiet': True, 'no_warnings': True, 'noprogress': True, 'noplaylist': True}
    if strategy == 'mweb_pot':
        base = get_pot_provider_opts() or get_yt_dlp_base_opts()
    elif strategy == 'android_vr':
        # Android VR 客戶端：不需 cookie、不需 n-challenge
        base['extractor_args'] = {'youtube': {'player_client': ['android_vr']}}
    elif strategy == 'android':
        # Android 客戶端不帶 cookie，不需要 n-challenge
        base['extractor_args'] = {'youtube': {'player_client': ['android']}}
    else:
        base = get_yt_dlp_base_opts()
    base['ffmpeg_location'] = str(Path(FFMPEG_PATH).parent)
    return base


def download_strategy_order(preferred: str) -> list[str]:
    """Return deterministic download fallbacks without trying a strategy twice."""
    ordered = [preferred]
    if POT_PROVIDER_URL:
        ordered.insert(0, 'mweb_pot')
    ordered.extend(['android_vr', 'android', 'web_creator'])
    return list(dict.fromkeys(ordered))


def cleanup_failed_download_files(task_dir: Path) -> None:
    """Remove files produced by a failed attempt inside its dedicated job folder."""
    for path in task_dir.iterdir():
        if path.is_file() or path.is_symlink():
            path.unlink()


def download_with_fallback(
    url: str,
    task_dir: Path,
    preferred_strategy: str,
    extra_opts: dict,
) -> str:
    """Download with a fresh extraction per client strategy and return the winner."""
    for strategy in download_strategy_order(preferred_strategy):
        opts = get_opts_for_strategy(strategy)
        opts.update(extra_opts)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return strategy
        except Exception as exc:
            cleanup_failed_download_files(task_dir)
            print(f'⚠️ 下載策略 ({strategy}) 失敗，嘗試下一個策略')
    raise RuntimeError('YouTube 暫時拒絕下載此影片，請稍後再試。')


def _try_extract(url: str, opts: dict, label: str):
    """嘗試用指定選項解析影片，成功回傳 info dict，失敗回傳 None"""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        # 檢查是否真的有影片/音訊格式（排除只有圖片的情況）
        formats = info.get('formats', [])
        has_media = any(
            f.get('vcodec', 'none') != 'none' or f.get('acodec', 'none') != 'none'
            for f in formats
        )
        if has_media:
            print(f'✅ {label} 解析成功（{len(formats)} 個格式）')
            return info
        else:
            print(f'⚠️ {label} 解析成功但沒有影音格式（可能 n-challenge 失敗）')
            return None
    except Exception as e:
        print(f'⚠️ {label} 解析失敗：{e}')
        return None


# ══════════════════════════════════════════
# API: 解析影片（不下載，只取得資訊與可用格式）
# ══════════════════════════════════════════
@app.post('/api/resolve')
async def resolve_video(req: ResolveRequest):
    """解析 YouTube 影片，回傳影片資訊與可用畫質"""
    try:
        url = validate_youtube_url(req.url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    info = None
    strategy_used = 'unknown'

    # ── 依序嘗試多種策略，每個策略獨立運作 ──
    strategies = []
    pot_opts = get_pot_provider_opts()
    if pot_opts:
        strategies.append(('mweb_pot', pot_opts))
    strategies.extend([
        # 策略 1：android_vr（不需 cookie、不需 n-challenge，最穩定）
        ('android_vr', {
            'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'extractor_args': {'youtube': {'player_client': ['android_vr']}},
        }),
        # 策略 2：android（不需 n-challenge）
        ('android', {
            'quiet': True, 'no_warnings': True, 'noplaylist': True,
            'extractor_args': {'youtube': {'player_client': ['android']}},
        }),
        # 策略 3：web_creator 不帶登入憑證
        ('web_creator', get_yt_dlp_base_opts()),
    ])

    for name, opts in strategies:
        if opts is None:
            continue
        info = _try_extract(url, opts, f'策略 ({name})')
        if info:
            strategy_used = name
            break

    # ── 全部失敗 ──
    if info is None:
        raise HTTPException(400,
            'YouTube 目前無法解析此影片。可能原因：\n'
            '• 影片可能有地區限制或年齡限制\n'
            '• YouTube 的反爬蟲機制正在阻擋\n'
            '請稍後再試，或嘗試另一個影片。'
        )

    job_id = str(uuid.uuid4())[:8]
    title = safe_filename(info.get('title', 'untitled'))

    # 分析可用格式，建立依畫質排序且包含音訊的大小估算。
    formats = info.get('formats', [])
    quality_options = build_quality_options(formats, info.get('duration', 0))
    best_height = quality_options[0]['height'] if quality_options else 0

    # 快取解析結果，供後續下載使用
    resolved_jobs[job_id] = {
        'url': url,
        'title': title,
        'raw_title': info.get('title', 'untitled'),
        'duration': info.get('duration', 0),
        'thumbnail': info.get('thumbnail', ''),
        'strategy': strategy_used,  # 記住用哪個策略成功的
        'qualities': quality_options,
    }

    return {
        'job_id': job_id,
        'title': info.get('title', 'untitled'),
        'thumbnail': info.get('thumbnail', ''),
        'duration': info.get('duration', 0),
        'best_quality': f"{best_height}p" if best_height else '未知',
        'available_qualities': [option['label'] for option in quality_options],
        'qualities': quality_options,
        'strategy': strategy_used,
    }


# ══════════════════════════════════════════
# API: 下載 MP4（SSE 進度串流）
# ══════════════════════════════════════════
@app.get('/api/process-mp4/{job_id}')
async def process_mp4(job_id: str, quality: int | None = None):
    """下載指定或最高畫質 MP4，透過 SSE 回報進度"""
    if job_id not in resolved_jobs:
        raise HTTPException(404, '工作不存在或已過期')

    job = resolved_jobs[job_id]
    available_heights = [option['height'] for option in job.get('qualities', [])]
    if not available_heights:
        raise HTTPException(400, '這支影片沒有可用的影片畫質')
    selected_quality = quality if quality is not None else available_heights[0]
    if selected_quality not in available_heights:
        raise HTTPException(400, '選擇的影片畫質不可用')

    async def generate():
        task_dir = DOWNLOAD_DIR / f"{job_id}_mp4"
        task_dir.mkdir(exist_ok=True)

        try:
            yield sse_event({
                'step': 'download',
                'progress': 5,
                'message': f'🎬 下載 {selected_quality}p 影片中...',
            })

            title = job['title']
            filename_stem = output_stem(title, 'mp4', selected_quality)
            format_str = quality_format_selector(selected_quality)

            # 共享進度狀態
            progress_state = {'pct': 5}

            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        progress_state['pct'] = 5 + int((downloaded / total) * 75)

            # 使用解析時成功的策略（有/無 cookie）
            download_opts = {
                'outtmpl': str(task_dir / f"{filename_stem}.%(ext)s"),
                'format': format_str,
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook],
            }

            loop = asyncio.get_event_loop()

            def do_download():
                winning_strategy = download_with_fallback(
                    job['url'], task_dir, job.get('strategy', 'android'), download_opts
                )
                job['strategy'] = winning_strategy

            # 在背景執行緒中下載，同時定期回報進度
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(do_download)

            while not future.done():
                yield sse_event({
                    'step': 'download',
                    'progress': min(progress_state['pct'], 80),
                    'message': f'🎬 下載 {selected_quality}p 影片中... {progress_state["pct"]}%',
                })
                await asyncio.sleep(1.2)

            # 檢查是否有錯誤
            exc = future.exception()
            if exc:
                raise exc

            yield sse_event({'step': 'download', 'progress': 85, 'message': '🎬 下載完成，檢查播放相容性...'})

            # 找到下載的影片檔案
            video_file = None
            for f in task_dir.iterdir():
                if f.suffix in ('.mp4', '.webm', '.mkv') and f.is_file() and not f.name.startswith('_'):
                    video_file = f
                    break

            if not video_file:
                yield sse_event({'step': 'error', 'message': '❌ 找不到下載的影片檔案'})
                return

            actual_height = probe_video_height(video_file)
            if actual_height != selected_quality:
                video_file.unlink(missing_ok=True)
                raise RuntimeError(
                    f'下載結果是 {actual_height}p，與所選的 {selected_quality}p 不符，'
                    '已取消儲存，請稍後再試。'
                )

            requires_conversion = not is_playback_compatible(
                probe_media_streams(video_file),
                video_file,
            )
            if requires_conversion:
                compatibility_future = loop.run_in_executor(
                    None,
                    ensure_playback_compatible,
                    video_file,
                )
                while not compatibility_future.done():
                    yield sse_event({
                        'step': 'download',
                        'progress': 90,
                        'message': '🎬 正在轉換成 Mac／Windows 相容格式...',
                    })
                    await asyncio.sleep(1.2)
                video_file, converted = await compatibility_future
            else:
                converted = False

            actual_height = probe_video_height(video_file)
            if actual_height != selected_quality:
                video_file.unlink(missing_ok=True)
                raise RuntimeError('相容格式轉換後的畫質與選擇不符。')

            video_file, saved_to = publish_completed_file(job_id, 'mp4', video_file)
            file_size = format_bytes(video_file.stat().st_size)

            yield sse_event({
                'step': 'done',
                'progress': 100,
                'message': (
                    f'✅ {selected_quality}p MP4 下載完成！'
                    if not converted
                    else f'✅ {selected_quality}p MP4 已轉為相容格式！'
                ),
                'download_url': f'/api/file/{job_id}/mp4',
                'preview_url': f'/api/preview/{job_id}/mp4',
                'filename': video_file.name,
                'filesize': file_size,
                'saved_to': saved_to,
                'quality': selected_quality,
            })

        except Exception as e:
            error_msg = str(e)
            if 'format' in error_msg.lower() and 'not available' in error_msg.lower():
                error_msg = '影片格式目前不可用，請稍後重試或改用另一支公開影片。'
            yield sse_event({'step': 'error', 'message': f'❌ {error_msg}'})
            traceback.print_exc()

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# ══════════════════════════════════════════
# API: 下載 MP3（SSE 進度串流）
# ══════════════════════════════════════════
@app.get('/api/process-mp3/{job_id}')
async def process_mp3(job_id: str):
    """下載音訊並轉換為 MP3，透過 SSE 回報進度"""
    if job_id not in resolved_jobs:
        raise HTTPException(404, '工作不存在或已過期')

    job = resolved_jobs[job_id]

    async def generate():
        task_dir = DOWNLOAD_DIR / f"{job_id}_mp3"
        task_dir.mkdir(exist_ok=True)

        try:
            yield sse_event({'step': 'download', 'progress': 5, 'message': '🎵 下載音訊中...'})

            title = job['title']
            filename_stem = output_stem(title, 'mp3')
            # 音訊格式策略：優先 m4a，再試其他音訊格式
            format_str = 'bestaudio[ext=m4a]/bestaudio/best'

            download_opts = {
                'outtmpl': str(task_dir / f"{filename_stem}.%(ext)s"),
                'format': format_str,
            }

            loop = asyncio.get_event_loop()

            def do_download():
                winning_strategy = download_with_fallback(
                    job['url'], task_dir, job.get('strategy', 'android'), download_opts
                )
                job['strategy'] = winning_strategy

            await loop.run_in_executor(None, do_download)

            yield sse_event({'step': 'convert', 'progress': 50, 'message': '🔄 轉換 MP3 中...'})

            # 找到下載的音訊檔案
            src_audio = None
            for f in task_dir.iterdir():
                if f.suffix in ('.m4a', '.webm', '.ogg', '.opus', '.mp4', '.mp3') and f.is_file():
                    src_audio = f
                    break

            if not src_audio:
                yield sse_event({'step': 'error', 'message': '❌ 找不到音訊檔案'})
                return

            mp3_path = task_dir / f"{filename_stem}.mp3"

            # 如果已經是 MP3 就不用轉了
            if src_audio.suffix == '.mp3':
                mp3_path = src_audio
            else:
                def do_convert():
                    subprocess.run([
                        FFMPEG_PATH, '-i', str(src_audio),
                        '-vn', '-acodec', 'libmp3lame', '-ab', '192k',
                        '-y', str(mp3_path)
                    ], capture_output=True, check=True)

                await loop.run_in_executor(None, do_convert)

            mp3_path, saved_to = publish_completed_file(job_id, 'mp3', mp3_path)
            file_size = format_bytes(mp3_path.stat().st_size)

            yield sse_event({
                'step': 'done',
                'progress': 100,
                'message': '✅ MP3 轉換完成！',
                'download_url': f'/api/file/{job_id}/mp3',
                'filename': mp3_path.name,
                'filesize': file_size,
                'saved_to': saved_to,
            })

        except Exception as e:
            yield sse_event({'step': 'error', 'message': f'❌ 轉換失敗：{str(e)}'})
            traceback.print_exc()

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# ══════════════════════════════════════════
# API: 產生逐字稿（SSE 進度串流）
# ══════════════════════════════════════════
@app.get('/api/process-transcript/{job_id}')
async def process_transcript(job_id: str, language: str = 'zh-TW'):
    """下載音訊 → Whisper 辨識 → 產生逐字稿，透過 SSE 回報進度"""
    if job_id not in resolved_jobs:
        raise HTTPException(404, '工作不存在或已過期')
    if language not in TRANSCRIPT_LANGUAGES:
        raise HTTPException(400, '逐字稿語言只支援繁體中文或英文雙語')

    job = resolved_jobs[job_id]

    async def generate():
        task_dir = DOWNLOAD_DIR / f"{job_id}_txt"
        task_dir.mkdir(exist_ok=True)

        try:
            yield sse_event({'step': 'download', 'progress': 5, 'message': '🎵 下載音訊中...'})

            title = job['title']
            transcript_stem = output_stem(
                title,
                'transcript',
                transcript_language=language,
            )

            download_opts = {
                'outtmpl': str(task_dir / f"{title}.%(ext)s"),
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
            }

            loop = asyncio.get_event_loop()

            def do_download():
                winning_strategy = download_with_fallback(
                    job['url'], task_dir, job.get('strategy', 'android'), download_opts
                )
                job['strategy'] = winning_strategy

            await loop.run_in_executor(None, do_download)

            yield sse_event({'step': 'convert', 'progress': 25, 'message': '🔄 轉換音訊格式中...'})

            # 找到下載的音訊檔案
            src_audio = None
            for f in task_dir.iterdir():
                if f.suffix in ('.m4a', '.webm', '.ogg', '.opus', '.mp4', '.mp3') and f.is_file():
                    src_audio = f
                    break

            if not src_audio:
                yield sse_event({'step': 'error', 'message': '❌ 找不到音訊檔案'})
                return

            # 轉成 WAV 給 Whisper 使用
            wav_path = task_dir / '_temp.wav'

            def do_wav_convert():
                subprocess.run([
                    FFMPEG_PATH, '-i', str(src_audio),
                    '-vn', '-ar', '16000', '-ac', '1',
                    '-y', str(wav_path)
                ], capture_output=True, check=True)

            await loop.run_in_executor(None, do_wav_convert)

            yield sse_event({
                'step': 'transcribe',
                'progress': 35,
                'message': '🧠 高品質 AI 語音辨識中（首次會先下載模型）...',
            })

            def do_transcribe():
                model = get_whisper_model()
                return model.transcribe(
                    str(wav_path),
                    language='zh' if language == 'zh-TW' else 'en',
                    task='transcribe',
                    fp16=False,
                    verbose=False,
                )

            transcribe_future = loop.run_in_executor(None, do_transcribe)
            while not transcribe_future.done():
                yield sse_event({
                    'step': 'transcribe',
                    'progress': 50,
                    'message': '🧠 高品質 AI 語音辨識中（這可能需要幾分鐘）...',
                })
                await asyncio.sleep(1.2)
            result = await transcribe_future
            segments = normalize_transcript_segments(result)
            if not segments:
                raise RuntimeError('沒有辨識到可輸出的語音內容')

            translations = None
            if language == 'en':
                yield sse_event({
                    'step': 'translate',
                    'progress': 75,
                    'message': '🌐 逐段翻譯成繁體中文（首次會先下載模型）...',
                })

                translate_future = loop.run_in_executor(
                    None,
                    translate_english_segments,
                    [segment['text'] for segment in segments],
                )
                while not translate_future.done():
                    yield sse_event({
                        'step': 'translate',
                        'progress': 85,
                        'message': '🌐 正在產生英中雙語段落...',
                    })
                    await asyncio.sleep(1.2)
                translations = await translate_future

            txt_path = task_dir / f"{transcript_stem}.txt"
            raw_title = job.get('raw_title', title)
            transcript_text = render_transcript(
                raw_title,
                language,
                segments,
                translations,
            )
            txt_path.write_text(transcript_text, encoding='utf-8')

            # 清理暫存 WAV
            if wav_path.exists():
                wav_path.unlink()

            txt_path, saved_to = publish_completed_file(job_id, 'transcript', txt_path)
            file_size = format_bytes(txt_path.stat().st_size)

            yield sse_event({
                'step': 'done',
                'progress': 100,
                'message': '✅ 逐字稿產生完成！',
                'download_url': f'/api/file/{job_id}/transcript',
                'filename': txt_path.name,
                'filesize': file_size,
                'saved_to': saved_to,
                'preview': (
                    transcript_text[:900]
                    + ('...' if len(transcript_text) > 900 else '')
                ),
                'language': language,
                'segments': len(segments),
            })

        except Exception as e:
            yield sse_event({'step': 'error', 'message': f'❌ 逐字稿產生失敗：{str(e)}'})
            traceback.print_exc()

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


# ══════════════════════════════════════════
# API: 檔案下載
# ══════════════════════════════════════════
@app.get('/api/file/{job_id}/{kind}')
async def download_file(job_id: str, kind: str):
    """回傳已處理完成的檔案供使用者下載"""
    filepath = registered_output_file(job_id, kind)

    # 根據副檔名判斷 Content-Type
    ext = filepath.suffix.lower()
    media_types = {
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mpeg',
        '.txt': 'text/plain; charset=utf-8',
    }

    return FileResponse(
        str(filepath),
        filename=filepath.name,
        media_type=media_types.get(ext, 'application/octet-stream'),
    )


@app.get('/api/preview/{job_id}/mp4')
async def preview_video(job_id: str):
    """Stream a registered MP4 inline for the local page video player."""
    filepath = registered_output_file(job_id, 'mp4')
    media_types = {
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
        '.mkv': 'video/x-matroska',
    }
    media_type = media_types.get(filepath.suffix.lower())
    if media_type is None:
        raise HTTPException(409, '這個影片格式無法在頁面中預覽')
    return FileResponse(
        str(filepath),
        media_type=media_type,
        headers={'Cache-Control': 'no-store'},
    )


@app.post('/api/open-folder/{job_id}/{kind}')
async def open_completed_output_folder(job_id: str, kind: str):
    """Open the containing folder for a registered desktop output."""
    filepath = registered_output_file(job_id, kind)
    if not IS_DESKTOP:
        raise HTTPException(400, '開啟資料夾功能僅支援桌面版')

    try:
        open_folder(filepath.parent)
    except OSError as exc:
        raise HTTPException(500, '無法開啟存放資料夾') from exc
    return {'status': 'ok', 'folder': filepath.parent.name}


@app.get('/api/health')
async def health():
    """Unauthenticated loopback readiness probe for the desktop launcher."""
    return {
        'status': 'ok',
        'product': PRODUCT_NAME,
        'version': APP_VERSION,
        'mode': 'desktop' if IS_DESKTOP else ('cloud' if IS_CLOUD else 'local'),
        'tools': {
            'ffmpeg': Path(FFMPEG_PATH).is_file(),
            'ffprobe': Path(FFPROBE_PATH).is_file(),
            'node': Path(NODE_PATH).is_file(),
            'quality_provider': bool(POT_PROVIDER_URL and POT_PLUGIN_READY),
        },
    }


@app.get('/launch')
async def launch(token: str = ''):
    """Exchange the launcher's URL value for a same-site session cookie."""
    if not LOCAL_SESSION_TOKEN:
        return RedirectResponse('/')
    if not secrets.compare_digest(token, LOCAL_SESSION_TOKEN):
        raise HTTPException(401, '無效的本機啟動憑證')

    response = RedirectResponse('/', status_code=303)
    response.set_cookie(
        LOCAL_SESSION_COOKIE,
        LOCAL_SESSION_TOKEN,
        httponly=True,
        samesite='strict',
        secure=False,
    )
    return response


@app.middleware('http')
async def desktop_local_session(request: Request, call_next):
    """Prevent unrelated websites from invoking the desktop localhost API."""
    if LOCAL_SESSION_TOKEN:
        if request.url.hostname not in {'127.0.0.1', 'localhost'}:
            return JSONResponse({'detail': '不允許的本機主機名稱'}, status_code=400)

        origin = request.headers.get('origin')
        if origin:
            parsed_origin = urlparse(origin)
            request_port = request.url.port or 80
            origin_port = parsed_origin.port or 80
            if (
                parsed_origin.scheme != 'http'
                or parsed_origin.hostname not in {'127.0.0.1', 'localhost'}
                or origin_port != request_port
            ):
                return JSONResponse({'detail': '不允許的本機來源'}, status_code=403)

        if request.url.path.startswith('/api/') and request.url.path != '/api/health':
            supplied = request.cookies.get(LOCAL_SESSION_COOKIE, '')
            if not secrets.compare_digest(supplied, LOCAL_SESSION_TOKEN):
                return JSONResponse({'detail': '請從桌面程式開啟 YT Downloader'}, status_code=401)
    return await call_next(request)


# ── 靜態檔案（放最後，避免覆蓋 API 路由） ──
app.mount('/', StaticFiles(directory=str(RESOURCE_DIR / 'static'), html=True), name='static')


# ── 啟動 ──
if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    host = '0.0.0.0' if IS_CLOUD else '127.0.0.1'
    print(f"🚀 {PRODUCT_NAME} 已啟動 — http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
