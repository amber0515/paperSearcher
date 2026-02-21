"""
论文摘要获取器

组合调度 Crossref、Semantic Scholar 和网页爬取获取论文摘要。
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

from .doi_extractor import extract_doi_from_origin, extract_arxiv_id
from .api_providers import get_crossref_client, get_semantic_scholar_client, get_openalex_client
from .origin_extractors import get_extractor, get_llm_extractor

logger = logging.getLogger(__name__)


class AbstractFetcher:
    """论文摘要获取器"""

    def __init__(self):
        self.crossref = get_crossref_client()
        self.openalex = get_openalex_client()
        self.semantic_scholar = get_semantic_scholar_client()
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

        优先级: Crossref -> OpenAlex -> Semantic Scholar -> 爬取原始网站

        Args:
            title: 论文标题
            href: DBLP 详情页链接
            origin: 原始会议/期刊网站链接

        Returns:
            (abstract, source) 元组，失败时 (None, None)
        """
        # 1. 提取 DOI
        doi = extract_doi_from_origin(origin, href)

        # 1.5 尝试提取 arXiv ID
        arxiv_id = extract_arxiv_id(origin) or extract_arxiv_id(href)
        if arxiv_id:
            # 尝试使用 arXiv ID 获取摘要
            abstract = await self._fetch_semantic_scholar_arxiv(arxiv_id)
            if abstract:
                return abstract, "semantic_scholar"

        # 2. 有 DOI 时尝试 Crossref
        if doi:
            abstract = await self._fetch_crossref(doi)
            if abstract:
                return abstract, "crossref"

            # TODO: 临时注释掉 OpenAlex 和 Semantic Scholar，测试 LLM 提取
            # # 3. 尝试 OpenAlex (DOI)
            # abstract = await self._fetch_openalex(doi)
            # if abstract:
            #     return abstract, "openalex"
            #
            # # 4. 尝试 Semantic Scholar (DOI)
            # abstract = await self._fetch_semantic_scholar(doi)
            # if abstract:
            #     return abstract, "semantic_scholar"
        else:
            # TODO: 临时注释掉 OpenAlex 和 Semantic Scholar，测试 LLM 提取
            # 没有 DOI 时，先尝试 OpenAlex 标题搜索
            # abstract = await self._search_openalex_by_title(title)
            # if abstract:
            #     return abstract, "openalex"
            #
            # # 没有 DOI 时，通过标题搜索 Semantic Scholar
            # abstract = await self._search_semantic_scholar_by_title(title)
            # if abstract:
            #     return abstract, "semantic_scholar"
            # 如果标题搜索失败（可能是 429），也尝试爬取原网页
            pass

        # 5. 爬取原始网站（仅当是有效的原始网站链接，不是 DBLP 列表页）
        if origin and 'dblp' not in origin.lower():
            abstract, source = await self._crawl_origin(origin, title)
            if abstract:
                return abstract, source

        return None, None

    async def _fetch_crossref(self, doi: str) -> Optional[str]:
        """从 Crossref 获取摘要"""
        try:
            return self.crossref.get_abstract(doi)
        except Exception as e:
            logger.debug(f"Crossref error for {doi}: {e}")
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

    async def _fetch_semantic_scholar(self, doi: str) -> Optional[str]:
        """从 Semantic Scholar 获取摘要"""
        try:
            return self.semantic_scholar.get_abstract(doi)
        except Exception as e:
            logger.debug(f"Semantic Scholar error for {doi}: {e}")
            return None

    async def _fetch_semantic_scholar_arxiv(self, arxiv_id: str) -> Optional[str]:
        """从 Semantic Scholar 获取 arXiv 论文摘要"""
        try:
            return self.semantic_scholar.get_abstract_arxiv(arxiv_id)
        except Exception as e:
            logger.debug(f"Semantic Scholar error for arXiv {arxiv_id}: {e}")
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
