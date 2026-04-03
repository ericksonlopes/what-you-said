import re
import tempfile
import httpx
import anyio
from typing import Any, List, Dict
from langchain_core.documents import Document
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from src.config.logger import Logger
from src.domain.interfaces.extractors.base_extractor_interface import IBaseExtractor

logger = Logger()


class Crawl4AIExtractor(IBaseExtractor):
    """
    Extractor implementation using Crawl4AI for high-quality web scraping.
    Supports JavaScript rendering and LLM-friendly output.
    """

    def __init__(self, headless: bool = True):
        # Using a realistic user agent to bypass anti-bot protection
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        self.browser_config = BrowserConfig(
            headless=headless,
            viewport_width=1280,
            viewport_height=720,
            user_agent=self.user_agent,
            extra_args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-audio-output",
            ],
        )

    async def extract(self, source: str, **kwargs: Any) -> List[Document]:
        """
        Extracts content from a URL using Crawl4AI.
        Detects PDF and falls back to Docling for better handling and bypassing anti-bot.
        """
        logger.info("Scraping web content", context={"url": source})

        # 1. Specialized handling for PDF URLs to bypass anti-bot and extraction errors
        if source.lower().endswith(".pdf") or kwargs.get("is_pdf", False):
            return await self._extract_pdf_directly(source, **kwargs)

        # 2. Configure Crawler
        run_config = self._build_run_config(kwargs)
        exclude_links = kwargs.get("exclude_links", True)

        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                # 3. Main Page Extraction
                result = await crawler.arun(url=source, config=run_config)

                if not result.success:
                    return await self._handle_crawl_failure(result, source, kwargs)

                documents = self._build_main_documents(result, source, exclude_links)

                # 4. Multi-depth crawl if requested
                depth = kwargs.get("depth", 1)
                if depth > 1:
                    sub_docs = await self._crawl_sub_pages(
                        crawler, result, source, run_config, kwargs
                    )
                    documents.extend(sub_docs)

                return documents
        except Exception as e:
            logger.error(e, context={"url": source, "action": "web_scrape"})
            raise

    def _build_run_config(self, kwargs: Dict[str, Any]) -> CrawlerRunConfig:
        return CrawlerRunConfig(
            css_selector=kwargs.get("css_selector"),
            word_count_threshold=kwargs.get("word_count_threshold", 200),
            cache_mode=CacheMode.BYPASS
            if kwargs.get("bypass_cache", True)
            else CacheMode.ENABLED,
        )

    async def _handle_crawl_failure(
        self, result: Any, source: str, kwargs: Dict[str, Any]
    ) -> List[Document]:
        # FALLBACK: If blocked by anti-bot or structural error (common for PDFs), try direct download
        if (
            "Blocked by anti-bot" in result.error_message
            or "Structural" in result.error_message
        ):
            logger.warning(
                "Crawl4AI blocked or failed structurally, trying direct download fallback",
                context={"url": source, "error": result.error_message},
            )
            try:
                return await self._extract_pdf_directly(source, **kwargs)
            except Exception as e:
                logger.error(f"Fallback direct extraction failed: {e}")

        logger.error(
            "Crawl4AI failed to scrape",
            context={"url": source, "error": result.error_message},
        )
        raise ValueError(f"Failed to scrape {source}: {result.error_message}")

    def _clean_markdown(self, text: str, exclude_links: bool) -> str:
        if not exclude_links:
            return text
        return re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)

    def _build_main_documents(
        self, result: Any, source: str, exclude_links: bool
    ) -> List[Document]:
        main_markdown = self._clean_markdown(result.markdown, exclude_links)
        metadata = {
            "source": source,
            "title": result.metadata.get("title", "") if result.metadata else "",
            "source_type": "web",
            "scraper": "crawl4ai",
            "status_code": result.status_code,
            "depth": 1,
        }
        return [Document(page_content=main_markdown, metadata=metadata)]

    async def _crawl_sub_pages(
        self,
        crawler: AsyncWebCrawler,
        result: Any,
        source: str,
        run_config: CrawlerRunConfig,
        kwargs: Dict[str, Any],
    ) -> List[Document]:
        depth = kwargs.get("depth", 1)
        max_sub_pages = kwargs.get("max_sub_pages", 10)
        concurrency_count = kwargs.get("concurrency_count", 2)
        exclude_links = kwargs.get("exclude_links", True)

        logger.info(
            "Extracting links for multi-depth crawl",
            context={"source": source, "depth": depth},
        )
        internal_links = result.links.get("internal", [])
        sub_urls = list(
            {
                link["href"]
                for link in internal_links
                if link.get("href") and link["href"].startswith("http")
            }
        )

        if not sub_urls:
            return []

        sub_urls = [u for u in sub_urls if u.split("#")[0] != source.split("#")[0]]
        sub_urls = sub_urls[:max_sub_pages]

        if not sub_urls:
            return []

        sub_results = await crawler.arun_many(
            urls=sub_urls, config=run_config, concurrency_count=concurrency_count
        )

        documents = []
        for sub_res in sub_results:
            if sub_res.success:
                sub_metadata = {
                    "source": sub_res.url,
                    "title": sub_res.metadata.get("title", "")
                    if sub_res.metadata
                    else "",
                    "source_type": "web",
                    "scraper": "crawl4ai",
                    "status_code": sub_res.status_code,
                    "depth": 2,
                    "parent_source": source,
                }
                documents.append(
                    Document(
                        page_content=self._clean_markdown(
                            sub_res.markdown, exclude_links
                        ),
                        metadata=sub_metadata,
                    )
                )
        return documents

    async def _extract_pdf_directly(self, url: str, **kwargs: Any) -> List[Document]:
        """
        Bypasses anti-bot by downloading PDF directly with realistic headers and using Docling.
        """
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        logger.info("Performing direct PDF extraction bypass", context={"url": url})

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/pdf,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, verify=True) as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()

                # Basic Content-Type check to confirm it's actually a PDF
                content_type = response.headers.get("Content-Type", "").lower()
                if "application/pdf" not in content_type and not url.lower().endswith(
                    ".pdf"
                ):
                    logger.warning(
                        "URL might not be a PDF",
                        context={"url": url, "content_type": content_type},
                    )

                # Fix: Use anyio.to_thread.run_sync for synchronous tempfile operations if needed,
                # or just create a path and use anyio for I/O.
                def create_temp_file():
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".pdf"
                    ) as tmp:
                        return tmp.name

                tmp_path = await anyio.to_thread.run_sync(create_temp_file)

                # Async file write to satisfy SonarQube
                await anyio.Path(tmp_path).write_bytes(response.content)

                try:
                    extractor = DoclingExtractor()
                    docs = extractor.extract(tmp_path)

                    for doc in docs:
                        doc.metadata["source"] = url
                        doc.metadata["source_type"] = "pdf"
                        doc.metadata["scraper"] = "docling_bypass"

                    return docs
                finally:
                    if await anyio.Path(tmp_path).exists():
                        await anyio.Path(tmp_path).unlink()

        except Exception as e:
            logger.error(
                f"Direct PDF download failed or extraction failed: {e}",
                context={"url": url},
            )
            raise ValueError(f"Failed to extract PDF directly from {url}: {str(e)}")
