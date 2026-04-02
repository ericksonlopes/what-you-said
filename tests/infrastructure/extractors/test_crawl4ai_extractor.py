import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.infrastructure.extractors.crawl4ai_extractor import Crawl4AIExtractor
from langchain_core.documents import Document


@pytest.mark.anyio
class TestCrawl4AIExtractor:
    async def test_extract_success(self):
        # Setup
        url = "https://example.com"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Example Content [link](http://link.com)"
        mock_result.metadata = {"title": "Example Domain"}
        mock_result.status_code = 200

        # Mock AsyncWebCrawler
        with patch(
            "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value = mock_crawler

            extractor = Crawl4AIExtractor()
            docs = await extractor.extract(url, exclude_links=True)

            # Assertions
            assert len(docs) == 1
            assert isinstance(docs[0], Document)
            # Link should be cleaned
            assert docs[0].page_content == "# Example Content link"
            assert docs[0].metadata["title"] == "Example Domain"
            assert docs[0].metadata["source"] == url

            mock_crawler.arun.assert_called_once()
            _, kwargs = mock_crawler.arun.call_args
            assert kwargs["url"] == url

    async def test_extract_not_exclude_links(self):
        url = "https://example.com"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "[link](http://link.com)"
        mock_result.metadata = {}

        with patch(
            "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value = mock_crawler

            extractor = Crawl4AIExtractor()
            docs = await extractor.extract(url, exclude_links=False)

            assert docs[0].page_content == "[link](http://link.com)"

    async def test_extract_failed_result(self):
        url = "https://example.com"
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "Crawl error"

        with patch(
            "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value = mock_crawler

            extractor = Crawl4AIExtractor()
            with pytest.raises(ValueError, match="Failed to scrape"):
                await extractor.extract(url)

    async def test_extract_with_selector(self):
        url = "https://example.com"
        selector = ".main-content"

        mock_result = MagicMock()
        mock_result.success = True
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
            _, kwargs = mock_crawler.arun.call_args
            run_config = kwargs["config"]
            assert run_config.css_selector == selector

    async def test_extract_multi_depth_success(self):
        url = "https://example.com"
        depth = 2

        # Mock main result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "Main Page"
        mock_result.metadata = {"title": "Main"}
        mock_result.links = {"internal": [{"href": "https://example.com/sub"}]}
        mock_result.status_code = 200

        # Mock sub page result
        mock_sub_result = MagicMock()
        mock_sub_result.success = True
        mock_sub_result.url = "https://example.com/sub"
        mock_sub_result.markdown = "Sub Page"
        mock_sub_result.metadata = {"title": "Sub"}
        mock_sub_result.status_code = 200

        with patch(
            "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.arun.return_value = mock_result
            mock_crawler.arun_many.return_value = [mock_sub_result]
            mock_crawler_class.return_value = mock_crawler

            extractor = Crawl4AIExtractor()
            docs = await extractor.extract(url, depth=depth)

            assert len(docs) == 2
            assert docs[0].page_content == "Main Page"
            assert docs[1].page_content == "Sub Page"
            assert docs[1].metadata["depth"] == 2
            assert docs[1].metadata["parent_source"] == url

            mock_crawler.arun_many.assert_called_once()

    async def test_extract_multi_depth_no_links(self):
        url = "https://example.com"
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "Main Page"
        mock_result.links = {"internal": []}

        with patch(
            "src.infrastructure.extractors.crawl4ai_extractor.AsyncWebCrawler"
        ) as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__.return_value = mock_crawler
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value = mock_crawler

            extractor = Crawl4AIExtractor()
            docs = await extractor.extract(url, depth=2)

            assert len(docs) == 1
            mock_crawler.arun_many.assert_not_called()

    async def test_error_handling(self):
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
