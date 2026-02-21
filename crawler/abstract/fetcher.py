"""
论文摘要获取器

组合调度 Crossref、Semantic Scholar 和网页爬取获取论文摘要。
"""
import logging
import asyncio
from typing import Optional
from crawl4ai import AsyncWebCrawler

from .doi_extractor import extract_doi_from_origin, extract_arxiv_id
from .api_clients import get_crossref_client, get_semantic_scholar_client

logger = logging.getLogger(__name__)


class AbstractFetcher:
    """论文摘要获取器"""

    def __init__(self):
        self.crossref = get_crossref_client()
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

        优先级: Crossref -> Semantic Scholar -> 爬取原始网站

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

            # 3. 尝试 Semantic Scholar (DOI)
            abstract = await self._fetch_semantic_scholar(doi)
            if abstract:
                return abstract, "semantic_scholar"
        else:
            # 没有 DOI 时，通过标题搜索 Semantic Scholar
            abstract = await self._search_semantic_scholar_by_title(title)
            if abstract:
                return abstract, "semantic_scholar"
            # 如果标题搜索失败（可能是 429），也尝试爬取原网页

        # 4. 爬取原始网站（仅当是有效的原始网站链接，不是 DBLP 列表页）
        if origin and 'dblp' not in origin.lower():
            abstract = await self._crawl_origin(origin, title)
            if abstract:
                return abstract, "origin"

        return None, None

    async def _fetch_crossref(self, doi: str) -> Optional[str]:
        """从 Crossref 获取摘要"""
        try:
            return self.crossref.get_abstract(doi)
        except Exception as e:
            logger.debug(f"Crossref error for {doi}: {e}")
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

    async def _crawl_origin(self, origin: str, title: str) -> Optional[str]:
        """从原始网站爬取摘要"""
        try:
            # 过滤非 http URL
            if not origin.startswith('http'):
                return None

            crawler = await self._get_crawler()
            result = await crawler.arun(url=origin)

            if not result.success:
                logger.debug(f"Failed to crawl {origin}: {result.error_message}")
                return None

            # 提取摘要
            html = result.html
            abstract = self._extract_abstract_from_html(html)
            if abstract:
                return abstract

            return None

        except Exception as e:
            logger.debug(f"Crawl error for {origin}: {e}")
            return None

    def _extract_abstract_from_html(self, html: str) -> Optional[str]:
        """从 HTML 中提取摘要"""
        import re

        html_lower = html.lower()

        # 各种网站的摘要模式
        patterns = [
            # USENIX: <div class="field field-name-field-paper-description">
            (r'<div[^>]*class=["\'][^"\']*field-paper-description[^"\']*["\'][^>]*>.*?<p[^>]*>(.*?)</p>', re.DOTALL),

            # generic abstract class
            (r'<div[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</div>', re.DOTALL),

            # section with abstract
            (r'<section[^>]*class=["\'][^"\']*abstract[^"\']*["\'][^>]*>(.*?)</section>', re.DOTALL),

            # meta tag
            (r'<meta[^>]*name=["\']abstract["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),

            # abstract tag
            (r'<abstract[^>]*>(.*?)</abstract>', re.DOTALL),

            # data-abstract attribute
            (r'data-abstract=["\']([^"\']+)["\']', re.IGNORECASE),

            # schema.org abstract
            (r'"abstract":\s*"([^"]+)"', re.IGNORECASE),
        ]

        for pattern, flags in patterns:
            match = re.search(pattern, html, flags | re.IGNORECASE)
            if match:
                abstract = match.group(1)
                # 清理 HTML 标签
                abstract = re.sub(r'<[^>]+>', '', abstract)
                # 清理多余空白
                abstract = ' '.join(abstract.split())
                # 移除 HTML 实体
                abstract = abstract.replace('&nbsp;', ' ')
                abstract = abstract.replace('&amp;', '&')
                abstract = abstract.replace('&lt;', '<')
                abstract = abstract.replace('&gt;', '>')
                abstract = abstract.replace('&quot;', '"')
                if abstract and len(abstract) > 20:  # 确保不是太短的错误匹配
                    return abstract

        return None


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
