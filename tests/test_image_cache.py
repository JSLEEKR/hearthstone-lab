import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from src.collector.image_cache import ImageCacheManager
import httpx


@pytest.fixture
def tmp_cache_dir(tmp_path):
    return tmp_path / "card_cache"


@pytest.mark.asyncio
async def test_download_card_image(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        path = await manager.get_card_image("CS2_182")

    assert path.exists()
    assert path.name == "CS2_182.png"


@pytest.mark.asyncio
async def test_cache_hit_skips_download(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)
    tmp_cache_dir.mkdir(parents=True, exist_ok=True)
    cached = tmp_cache_dir / "CS2_182.png"
    cached.write_bytes(b"cached_image_data")

    with patch("httpx.AsyncClient.get") as mock_get:
        path = await manager.get_card_image("CS2_182")

    mock_get.assert_not_called()
    assert path == cached


@pytest.mark.asyncio
async def test_bulk_download_multiple(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.content = b"\x89PNG" + b"\x00" * 50
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        results = await manager.bulk_download(["CS2_182", "CS2_029"])

    assert len(results) == 2
    assert all(p.exists() for p in results.values())


@pytest.mark.asyncio
async def test_download_failure_returns_none(tmp_cache_dir):
    manager = ImageCacheManager(cache_dir=tmp_cache_dir)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock_response
    )

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        path = await manager.get_card_image("NONEXISTENT")

    assert path is None
