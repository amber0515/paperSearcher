"""
论文摘要获取器

组合调度 Crossref、Semantic Scholar 和网页爬取获取论文摘要。
"""
import logging
import asyncio
import os
from pathlib import Path
from typing import Optional
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy, create_llm_config

# 精简日志输出
for logger_name in ["crawl4ai", "litellm", "LiteLLM", "httpx", "urllib3", "asyncio"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# 加载 .env 文件
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from .doi_extractor import extract_doi_from_origin, extract_arxiv_id
from .api_clients import get_crossref_client, get_semantic_scholar_client, get_openalex_client

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
        1. 先尝试正则表达式匹配（固定处理流程）
        2. 正则匹配失败则使用 LLM 智能提取

        Returns:
            (abstract, source) - source 为 "origin_fixed" 或 "origin_llm"
        """
        # 过滤非 http URL
        if not origin.startswith('http'):
            return None, "origin"

        # 1. 先尝试爬取页面并用正则匹配
        try:
            crawler = await self._get_crawler()
            result = await crawler.arun(url=origin)

            if result.success and result.html:
                # 尝试正则提取
                abstract = self._extract_abstract_from_html(result.html)
                if abstract:
                    print(f"OK: origin_fixed extracted ({len(abstract)} chars)")
                    return abstract, "origin_fixed"
        except Exception as e:
            print(f"WARN: regex extraction failed: {e}")

        # 2. 正则匹配失败，使用 LLM 提取
        return await self._crawl_origin_llm(origin)

    async def _crawl_origin_llm(self, origin: str) -> tuple[Optional[str], str]:
        """使用 LLM 从原始网站提取摘要"""
        # LLM 配置（支持自定义 provider 和 base_url）
        # 环境变量:
        #   - LLM_PROVIDER: 提供商 (如 openai/gpt-4o-mini, anthropic/claude-3-sonnet, 等)
        #   - LLM_API_KEY: API 密钥
        #   - LLM_BASE_URL: 自定义 API 端点 (可选)
        llm_config = create_llm_config(
            provider=os.getenv("LLM_PROVIDER"),
            api_token=os.getenv("LLM_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL")
        )

        llm_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            instruction="Extract the research paper abstract from this webpage. Return only the abstract text, nothing else. If there is no abstract, return empty string.",
            input_format="markdown",
            verbose=False
        )

        config = CrawlerRunConfig(
            extraction_strategy=llm_strategy,
        )

        crawler = await self._get_crawler()
        result = await crawler.arun(url=origin, config=config)

        if not result.success:
            error_msg = f"Failed to crawl {origin}: {result.error_message}"
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        # 尝试从 LLM 提取结果获取摘要
        if result.extracted_content:
            # LLM 提取结果可能是 JSON 或纯文本
            try:
                import json
                data = json.loads(result.extracted_content)

                # 检查 JSON 中是否有 error 字段且为 true
                has_error = False
                if isinstance(data, list) and data:
                    has_error = data[0].get('error', False) is True
                elif isinstance(data, dict):
                    has_error = data.get('error', False) is True

                if has_error:
                    error_msg = f"LLM extraction error for {origin}: {result.extracted_content}"
                    print(f"ERROR: {error_msg}")
                    raise RuntimeError(error_msg)

                # 提取摘要内容
                abstract = None
                if isinstance(data, list) and data:
                    content = data[0].get('content')
                    # content 可能是列表或字符串
                    if isinstance(content, list):
                        abstract = ' '.join(str(c) for c in content)
                    else:
                        abstract = content
                    abstract = abstract or data[0].get('abstract', '')
                elif isinstance(data, dict):
                    content = data.get('content')
                    if isinstance(content, list):
                        abstract = ' '.join(str(c) for c in content)
                    else:
                        abstract = content
                    abstract = abstract or data.get('abstract', '')
                else:
                    abstract = str(data) if data else ''

                if abstract and len(abstract) > 20:
                    print(f"OK: origin_llm extracted ({len(abstract)} chars)")
                    return abstract, "origin_llm"

            except (json.JSONDecodeError, AttributeError):
                # 直接返回文本内容
                if result.extracted_content and len(result.extracted_content) > 20:
                    return result.extracted_content, "origin_llm"

        return None, "origin_llm"

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
