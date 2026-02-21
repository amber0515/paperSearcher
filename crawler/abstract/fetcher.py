"""
论文摘要获取器

调度多种方式获取论文摘要：arXiv API、原始网站提取（专用提取器 / LLM）。
"""
import logging
import asyncio
import os
from pathlib import Path
from typing import Optional
from crawl4ai import AsyncWebCrawler

# 精简日志输出
for logger_name in ["crawl4ai", "litellm", "LiteLLM", "httpx", "urllib3", "asyncio"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# 加载 .env 文件
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from .doi_extractor import extract_doi_from_origin
from .api_providers import get_semantic_scholar_client, get_openalex_client
from .origin_extractors import get_extractor, get_llm_extractor

logger = logging.getLogger(__name__)


class AbstractFetcher:
    """论文摘要获取器"""

    def __init__(self):
        self.semantic_scholar = get_semantic_scholar_client()
        self.openalex = get_openalex_client()
        self._crawler = None

    async def _get_crawler(self) -> AsyncWebCrawler:
        """获取爬虫实例（延迟初始化）"""
        if self._crawler is None:
            self._crawler = AsyncWebCrawler(verbose=False)
            await self._crawler.__aenter__()
        return self._crawler

    async def close(self):
        """关闭爬虫"""
        if self._crawler:
            await self._crawler.__aexit__(None, None, None)
            self._crawler = None

    async def fetch_abstract(
        self,
        title: str,
        href: str = "",
        origin: str = ""
    ) -> tuple[Optional[str], Optional[str]]:
        """
        获取论文摘要

        优先级:
        1. 有 DOI -> Semantic Scholar
        2. 无 DOI -> 标题搜索 OpenAlex -> Semantic Scholar
        3. 都失败 -> 原始网站提取 (专用提取器 / LLM)

        Args:
            title: 论文标题
            href: DBLP 详情页链接
            origin: 原始会议/期刊网站链接

        Returns:
            (abstract, source) 元组，失败时 (None, None)
        """
        # 1. 提取 DOI
        doi = extract_doi_from_origin(origin, href)
        if doi:
            logger.info(f"  → 尝试 Semantic Scholar (DOI: {doi})")
            abstract = await self._fetch_semantic_scholar(doi)
            if abstract:
                logger.info(f"  ✓ 成功 (来源: semantic_scholar)")
                return abstract, "semantic_scholar"
            logger.info(f"  ✗ 失败")

        # 2. 无 DOI 时，尝试标题搜索
        if not doi:
            logger.info(f"  → 尝试 OpenAlex (标题搜索)")
            abstract = await self._search_openalex_by_title(title)
            if abstract:
                logger.info(f"  ✓ 成功 (来源: openalex)")
                return abstract, "openalex"
            logger.info(f"  ✗ 失败")

            logger.info(f"  → 尝试 Semantic Scholar (标题搜索)")
            abstract = await self._search_semantic_scholar_by_title(title)
            if abstract:
                logger.info(f"  ✓ 成功 (来源: semantic_scholar)")
                return abstract, "semantic_scholar"
            logger.info(f"  ✗ 失败")

        # 3. 爬取原始网站
        if origin and 'dblp' not in origin.lower():
            logger.info(f"  → 尝试原始网站提取")
            abstract, source = await self._crawl_origin(origin, title)
            if abstract:
                logger.info(f"  ✓ 成功 (来源: {source})")
                return abstract, source

        logger.info(f"  ✗ 所有方式均失败")
        return None, None

    async def _fetch_semantic_scholar(self, doi: str) -> Optional[str]:
        """从 Semantic Scholar 获取摘要"""
        try:
            return self.semantic_scholar.get_abstract(doi)
        except Exception as e:
            logger.debug(f"Semantic Scholar error for {doi}: {e}")
            return None

    async def _fetch_openalex(self, doi: str) -> Optional[str]:
        """从 OpenAlex 获取摘要"""
        try:
            return self.openalex.get_abstract(doi)
        except Exception as e:
            logger.debug(f"OpenAlex error for {doi}: {e}")
            return None

    async def _search_openalex_by_title(self, title: str) -> Optional[str]:
        """通过标题在 OpenAlex 搜索获取摘要"""
        try:
            return self.openalex.search_by_title(title)
        except Exception as e:
            logger.debug(f"OpenAlex search error for '{title}': {e}")
            return None

    async def _search_semantic_scholar_by_title(self, title: str) -> Optional[str]:
        """通过标题在 Semantic Scholar 搜索获取摘要"""
        try:
            return self.semantic_scholar.search_by_title(title)
        except Exception as e:
            logger.debug(f"Semantic Scholar search error for '{title}': {e}")
            return None

    async def _crawl_origin(self, origin: str, title: str) -> tuple[Optional[str], str]:
        """
        从原始网站爬取摘要

        策略：
        1. 查找匹配的专用提取器
        2. 有提取器则使用提取器提取
        3. 没有提取器或提取失败则使用 LLM 提取器

        Returns:
            (abstract, source) - source 为 "origin_{name}" 或 "origin_llm"
        """
        # 过滤非 http URL
        if not origin.startswith('http'):
            return None, "origin"

        # 1. 查找匹配的提取器
        extractor = get_extractor(origin)

        # 2. 爬取页面
        try:
            crawler = await self._get_crawler()
            result = await crawler.arun(url=origin)

            if result.success and result.html:
                # 2.1 有专用提取器，使用提取器提取
                if extractor:
                    abstract = extractor.extract(result.html)
                    if abstract:
                        name = extractor.__class__.__name__.replace("Extractor", "").lower()
                        print(f"OK: origin_{name} extracted ({len(abstract)} chars)")
                        return abstract, f"origin_{name}"
        except Exception as e:
            print(f"WARN: extraction failed: {e}")

        # 3. 所有提取失败，使用 LLM 提取器
        llm_extractor = get_llm_extractor()
        return await llm_extractor.extract_async(origin)



def fetch_abstract_sync(
    title: str,
    href: str = "",
    origin: str = ""
) -> tuple[Optional[str], Optional[str]]:
    """
    同步版本的摘要获取器
    """
    fetcher = AbstractFetcher()
    try:
        return asyncio.run(fetcher.fetch_abstract(title, href, origin))
    finally:
        asyncio.run(fetcher.close())


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.DEBUG)

    test_cases = [
        {
            "title": "Attention Is All You Need",
            "href": "https://dblp.org/rec/conf/nips/VaswaniSPUJMDP18.html",
            "origin": "https://proceedings.neurips.cc/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html"
        },
    ]

    for case in test_cases:
        abstract, source = fetch_abstract_sync(**case)
        print(f"Title: {case['title']}")
        print(f"Abstract: {abstract}")
        print(f"Source: {source}")
        print()
