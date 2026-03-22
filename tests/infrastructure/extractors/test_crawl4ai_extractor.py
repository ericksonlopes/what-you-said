import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.infrastructure.extractors.crawl4ai_extractor import Crawl4AIExtractor
from langchain_core.documents import Document


@pytest.mark.anyio
async def test_crawl4ai_extractor_extract_success():
    # Setup
    url = "https://example.com"
    mock_result = MagicMock()
    mock_result.markdown = "# Example Content"
    mock_result.metadata = {"title": "Example Domain"}

    # Mock AsyncWebCrawler
    with patch(
        "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
    ) as mock_crawler_class:
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value = mock_crawler

        extractor = Crawl4AIExtractor()
        docs = await extractor.extract(url)

        # Assertions
        assert len(docs) == 1
        assert isinstance(docs[0], Document)
        assert docs[0].page_content == "# Example Content"
        assert docs[0].metadata["title"] == "Example Domain"
        assert docs[0].metadata["source"] == url

        mock_crawler.arun.assert_called_once()
        args, kwargs = mock_crawler.arun.call_args
        assert kwargs["url"] == url


@pytest.mark.anyio
async def test_crawl4ai_extractor_extract_with_selector():
    url = "https://example.com"
    selector = ".main-content"

    mock_result = MagicMock()
    mock_result.markdown = "Filtered Content"
    mock_result.metadata = {}

    with patch(
        "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
    ) as mock_crawler_class:
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value = mock_crawler

        extractor = Crawl4AIExtractor()
        await extractor.extract(url, css_selector=selector)

        # Verify selector was passed
        args, kwargs = mock_crawler.arun.call_args
        run_config = kwargs["config"]
        assert run_config.css_selector == selector


@pytest.mark.anyio
async def test_crawl4ai_extractor_error_handling():
    url = "https://invalid-url"

    with patch(
        "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
    ) as mock_crawler_class:
        mock_crawler = AsyncMock()
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.arun.side_effect = Exception("Crawl failed")
        mock_crawler_class.return_value = mock_crawler

        extractor = Crawl4AIExtractor()
        with pytest.raises(Exception) as excinfo:
            await extractor.extract(url)

        assert "Crawl failed" in str(excinfo.value)
