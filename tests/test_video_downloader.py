import requests
from unittest.mock import patch, MagicMock

from video_downloader import download_video_http


def test_download_video_http_success(tmp_path):
    output = tmp_path / "out.mp4"
    fake_response = MagicMock()
    fake_response.iter_content = lambda chunk_size: [b"FAKEVIDEO" * 12000]  # 12000 * 9 = 108000 bytes > 100KB
    fake_response.raise_for_status = MagicMock()
    with patch("video_downloader.requests.get", return_value=fake_response) as mock_get:
        result = download_video_http(
            url="https://example.com/v.mp4",
            output_path=str(output),
            cookies={"session": "abc"},
        )
    assert result is True
    assert output.read_bytes() == b"FAKEVIDEO" * 12000
    mock_get.assert_called_once_with(
        "https://example.com/v.mp4",
        cookies={"session": "abc"},
        stream=True,
        timeout=300,
    )


def test_download_video_http_failure_returns_false(tmp_path):
    output = tmp_path / "out.mp4"
    with patch("video_downloader.requests.get", side_effect=requests.ConnectionError("boom")):
        result = download_video_http(
            url="https://example.com/v.mp4",
            output_path=str(output),
            cookies={},
        )
    assert result is False
    assert not output.exists()


def test_download_video_http_min_size_check(tmp_path):
    output = tmp_path / "out.mp4"
    fake_response = MagicMock()
    fake_response.iter_content = lambda chunk_size: [b"x"]  # 1 byte
    fake_response.raise_for_status = MagicMock()
    with patch("video_downloader.requests.get", return_value=fake_response):
        result = download_video_http(
            url="https://example.com/v.mp4",
            output_path=str(output),
            cookies={},
            min_size_bytes=1024,
        )
    assert result is False  # rejected due to size