import pytest

from routers.user_guide_videos import extract_video_id


@pytest.mark.parametrize(
    ("url", "expected_id"),
    [
        ("https://www.youtube.com/watch?v=abc123", "abc123"),
        ("https://youtu.be/abc123", "abc123"),
        ("https://vimeo.com/123456789", "123456789"),
        ("https://www.vimeo.com/123456789/abcdef", "123456789"),
        ("https://player.vimeo.com/video/123456789", "123456789"),
        (
            "https://vimeo.com/groups/staffpicks/videos/123456789",
            "123456789",
        ),
    ],
)
def test_extract_video_id_accepts_youtube_and_vimeo_urls(url, expected_id):
    assert extract_video_id(url) == expected_id


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/video/123456789",
        "https://vimeo.com/",
        "vimeo.com/123456789",
    ],
)
def test_extract_video_id_rejects_unsupported_or_invalid_urls(url):
    with pytest.raises(ValueError):
        extract_video_id(url)
