from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app as app_module


def test_find_media_tool_accepts_packaged_windows_executable(tmp_path, monkeypatch):
    tool = tmp_path / "tools" / "ffmpeg.exe"
    tool.parent.mkdir(parents=True)
    tool.write_bytes(b"windows executable")
    tool.chmod(0o755)
    monkeypatch.setattr(app_module.sys, "platform", "win32")
    monkeypatch.setattr(app_module, "RESOURCE_DIR", tmp_path)
    monkeypatch.setattr(app_module, "BASE_DIR", tmp_path)

    assert app_module.find_media_tool("ffmpeg") == str(tool)


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "https://youtu.be/jNQXAC9IVRw",
        "https://music.youtube.com/watch?v=jNQXAC9IVRw",
    ],
)
def test_validate_youtube_url_accepts_supported_hosts(url):
    assert app_module.validate_youtube_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "http://youtube.com/watch?v=test",
        "https://youtube.com.evil.example/watch?v=test",
        "https://example.com/watch?v=test",
        "file:///etc/passwd",
        "https://user:password@youtube.com/watch?v=test",
        "https://youtube.com:444/watch?v=test",
        "https://youtube.com:not-a-port/watch?v=test",
    ],
)
def test_validate_youtube_url_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        app_module.validate_youtube_url(url)


def test_health_and_frontend_are_available():
    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["product"] == "YT Downloader by 學人新創"

    page = client.get("/")
    assert page.status_code == 200
    assert "id=\"card-transcript\"" in page.text
    assert "id=\"btn-transcript\"" in page.text
    assert "Cookie 設定" not in page.text


def test_resolve_rejects_non_youtube_url_before_extraction():
    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    response = client.post("/api/resolve", json={"url": "https://example.com/video"})
    assert response.status_code == 400


def test_file_endpoint_rejects_unregistered_output():
    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    response = client.get("/api/file/deadbeef/mp4")
    assert response.status_code == 404


def test_preview_endpoint_streams_registered_video_inline(tmp_path, monkeypatch):
    job_id = "1234abcd"
    output = tmp_path / "video.mp4"
    output.write_bytes(b"0123456789")
    monkeypatch.setattr(
        app_module,
        "resolved_jobs",
        {job_id: {"outputs": {"mp4": str(output)}}},
    )

    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    response = client.get(f"/api/preview/{job_id}/mp4")
    ranged = client.get(
        f"/api/preview/{job_id}/mp4",
        headers={"Range": "bytes=2-5"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert "content-disposition" not in response.headers
    assert ranged.status_code == 206
    assert ranged.content == b"2345"


def test_open_folder_uses_only_registered_desktop_output(tmp_path, monkeypatch):
    job_id = "1234abcd"
    folder = tmp_path / "260831_1427"
    folder.mkdir()
    output = folder / "video.mp4"
    output.write_bytes(b"video")
    opened = []

    monkeypatch.setattr(app_module, "IS_DESKTOP", True)
    monkeypatch.setattr(
        app_module,
        "resolved_jobs",
        {job_id: {"outputs": {"mp4": str(output)}}},
    )
    monkeypatch.setattr(app_module, "open_folder", lambda path: opened.append(path))

    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    response = client.post(f"/api/open-folder/{job_id}/mp4")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "folder": "260831_1427"}
    assert opened == [folder.resolve()]
    assert client.post(f"/api/open-folder/{job_id}/transcript").status_code == 404


def test_desktop_session_requires_cookie_and_valid_origin(monkeypatch):
    monkeypatch.setattr(app_module, "LOCAL_SESSION_TOKEN", "test-token")
    client = TestClient(app_module.app, base_url="http://127.0.0.1:18765")

    assert client.get("/api/health").status_code == 200
    assert client.post("/api/resolve", json={"url": "https://example.com"}).status_code == 401

    launched = client.get("/launch?token=test-token", follow_redirects=False)
    assert launched.status_code == 303
    assert launched.cookies.get(app_module.LOCAL_SESSION_COOKIE) == "test-token"

    client.cookies.set(app_module.LOCAL_SESSION_COOKIE, "test-token")
    rejected = client.post(
        "/api/resolve",
        json={"url": "https://example.com"},
        headers={"Origin": "https://evil.example"},
    )
    assert rejected.status_code == 403


def test_static_ids_match_frontend_lookup():
    html = Path("static/index.html").read_text(encoding="utf-8")
    for task_type in ("mp4", "mp3", "transcript"):
        assert f'id="card-{task_type}"' in html
        assert f'id="btn-{task_type}"' in html
        assert f'id="open-folder-{task_type}"' in html
        assert f'id="result-actions-{task_type}"' in html
    assert 'id="quality-trigger"' in html
    assert 'id="quality-dialog"' in html
    assert 'id="quality-options"' in html
    assert '<select' not in html
    assert "預估值可能因 YouTube 串流合併而略有差異" not in html
    assert 'id="video-preview"' in html
    assert 'id="reset-btn"' not in html
    assert "再下載一個" not in html


def test_download_strategy_order_falls_back_from_resolve_strategy():
    assert app_module.download_strategy_order("android_vr") == [
        "android_vr",
        "android",
        "web_creator",
    ]
    assert app_module.download_strategy_order("android")[0] == "android"


def test_quality_options_include_audio_and_default_to_highest():
    formats = [
        {
            "ext": "m4a",
            "vcodec": "none",
            "acodec": "mp4a.40.2",
            "abr": 128,
            "filesize": 2_000_000,
        },
        {
            "ext": "mp4",
            "height": 720,
            "vcodec": "avc1",
            "acodec": "none",
            "fps": 30,
            "filesize": 8_000_000,
        },
        {
            "ext": "mp4",
            "height": 1080,
            "vcodec": "avc1",
            "acodec": "none",
            "fps": 60,
            "filesize": 18_000_000,
        },
    ]

    options = app_module.build_quality_options(formats, duration=120)

    assert [option["height"] for option in options] == [1080, 720]
    assert options[0]["estimated_size_bytes"] == 20_000_000
    assert options[1]["estimated_size_bytes"] == 10_000_000
    assert options[0]["estimated_size"] != "—"


def test_quality_format_selector_never_silently_falls_back_to_lower_height():
    selector = app_module.quality_format_selector(720)
    assert selector.startswith("bestvideo[height=720][ext=mp4]")
    assert "height<=720" not in selector
    assert "height=720" in selector


def test_download_strategy_prefers_pot_provider_when_available(monkeypatch):
    monkeypatch.setattr(app_module, "POT_PROVIDER_URL", "http://127.0.0.1:4416")
    assert app_module.download_strategy_order("android_vr") == [
        "mweb_pot",
        "android_vr",
        "android",
        "web_creator",
    ]


def test_pot_provider_options_use_mweb_and_local_provider(monkeypatch):
    monkeypatch.setattr(app_module, "POT_PROVIDER_URL", "http://127.0.0.1:4416")
    monkeypatch.setattr(app_module, "NODE_PATH", "/Applications/Test.app/node")

    opts = app_module.get_pot_provider_opts()

    assert opts["extractor_args"]["youtube"]["player_client"] == ["mweb"]
    assert opts["extractor_args"]["youtubepot-bgutilhttp"]["base_url"] == [
        "http://127.0.0.1:4416"
    ]


def test_local_provider_plugin_directory_is_registered():
    assert app_module.POT_PLUGIN_DIR is not None
    assert app_module.POT_PLUGIN_READY is True
    assert (app_module.POT_PLUGIN_DIR / "yt_dlp_plugins").is_dir()


def test_mp4_rejects_quality_not_returned_by_resolve(monkeypatch):
    monkeypatch.setattr(
        app_module,
        "resolved_jobs",
        {"1234abcd": {"qualities": [{"height": 720}]}},
    )
    client = TestClient(app_module.app, base_url="http://127.0.0.1")

    response = client.get("/api/process-mp4/1234abcd?quality=2160")

    assert response.status_code == 400
    assert response.json()["detail"] == "選擇的影片畫質不可用"


def test_timestamp_output_directory_avoids_same_minute_collision(tmp_path):
    now = datetime(2026, 8, 31, 14, 5)
    first = app_module.create_timestamp_output_dir(tmp_path, now, title="教學:剪輯 / 入門")
    second = app_module.create_timestamp_output_dir(tmp_path, now, title="教學:剪輯 / 入門")

    assert first.name == "教學_剪輯_入門_260831_1405"
    assert second.name == "教學_剪輯_入門_260831_1405_2"


def test_output_stems_prefix_video_title_and_identify_file_type():
    title = "教學:剪輯 / 入門"

    assert app_module.output_stem(title, "mp4", 720) == "教學_剪輯_入門_影片_720p"
    assert app_module.output_stem(title, "mp3") == "教學_剪輯_入門_音檔"
    assert app_module.output_stem(title, "transcript") == "教學_剪輯_入門_逐字稿"


def test_desktop_outputs_for_one_job_share_timestamp_folder(tmp_path, monkeypatch):
    job_id = "1234abcd"
    source_dir = tmp_path / "jobs"
    source_dir.mkdir()
    first_source = source_dir / "video.mp4"
    second_source = source_dir / "audio.mp3"
    first_source.write_bytes(b"video")
    second_source.write_bytes(b"audio")

    monkeypatch.setattr(app_module, "IS_DESKTOP", True)
    monkeypatch.setattr(app_module, "DESKTOP_PATHS", {"output": tmp_path / "Downloads"})
    monkeypatch.setattr(app_module, "resolved_jobs", {job_id: {"title": "測試影片"}})

    first, first_label = app_module.publish_completed_file(job_id, "mp4", first_source)
    second, second_label = app_module.publish_completed_file(job_id, "mp3", second_source)

    assert first.parent == second.parent
    assert first.parent.parent == tmp_path / "Downloads"
    assert first.parent.name.startswith("測試影片_")
    assert first_label == f"下載項目/{first.parent.name}"
    assert second_label == first_label
