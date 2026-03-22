from typing import Any, List
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
        self.browser_config = BrowserConfig(
            headless=headless,
            viewport_width=1280,
            viewport_height=720,
        )

    async def extract(self, source: str, **kwargs: Any) -> List[Document]:
        """
        Extracts content from a URL using Crawl4AI.

        Args:
            source: The URL to scrape.
            **kwargs:
                css_selector: Optional CSS selector to target specific content.
                word_count_threshold: Min words to keep a chunk.
                bypass_cache: Whether to ignore existing cache.

        Returns:
            List[Document]: A list containing the scraped content as a LangChain Document.
        """
        logger.info(f"Scraping web content from: {source}", context={"url": source})

        css_selector = kwargs.get("css_selector")
        word_count_threshold = kwargs.get("word_count_threshold", 200)
        bypass_cache = kwargs.get("bypass_cache", True)
        depth = kwargs.get("depth", 1)
        max_sub_pages = kwargs.get(
            "max_sub_pages", 10
        )  # Limit to 10 sub-pages per crawl

        run_config = CrawlerRunConfig(
            css_selector=css_selector,
            word_count_threshold=word_count_threshold,
            cache_mode=CacheMode.BYPASS if bypass_cache else CacheMode.ENABLED,
        )

        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                # 1. First Crawl (Landing Page)
                result = await crawler.arun(url=source, config=run_config)

                if not result.success:
                    logger.error(
                        f"Crawl4AI failed to scrape {source}: {result.error_message}"
                    )
                    raise ValueError(
                        f"Failed to scrape {source}: {result.error_message}"
                    )

                documents = []
                # Main page content
                main_markdown = result.markdown
                metadata = {
                    "source": source,
                    "title": result.metadata.get("title", "")
                    if result.metadata
                    else "",
                    "source_type": "web",
                    "scraper": "crawl4ai",
                    "status_code": result.status_code,
                    "depth": 1,
                }
                documents.append(
                    Document(page_content=main_markdown, metadata=metadata)
                )

                # 2. Handle Depth 2
                if depth > 1:
                    logger.info(
                        f"Depth {depth} requested. Extracting links from {source}..."
                    )

                    # Get internal links
                    internal_links = result.links.get("internal", [])
                    sub_urls = list(
                        set(
                            [
                                link["href"]
                                for link in internal_links
                                if link.get("href") and link["href"].startswith("http")
                            ]
                        )
                    )

                    # Filter and limit
                    if sub_urls:
                        # Exclude self and fragments
                        sub_urls = [
                            u
                            for u in sub_urls
                            if u.split("#")[0] != source.split("#")[0]
                        ]
                        sub_urls = sub_urls[:max_sub_pages]

                        if sub_urls:
                            logger.info(
                                f"Following {len(sub_urls)} internal links for Depth 2",
                                context={"sub_urls": sub_urls},
                            )
                            sub_results = await crawler.arun_many(
                                urls=sub_urls, config=run_config
                            )

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
                                            page_content=sub_res.markdown,
                                            metadata=sub_metadata,
                                        )
                                    )

                logger.info(
                    f"Successfully scraped web content with depth {depth}",
                    context={"url": source, "page_count": len(documents)},
                )

                return documents

        except Exception as e:
            logger.error(
                f"Unexpected error during Crawl4AI extraction: {e}",
                context={"url": source},
            )
            raise e
