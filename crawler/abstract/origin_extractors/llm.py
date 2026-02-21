"""LLM 提取器"""
import os
import json
import logging
from typing import Optional
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy, create_llm_config
from .base import BaseExtractor

logger = logging.getLogger(__name__)


class LLMExtractor(BaseExtractor):
    """LLM 提取器 - 使用大语言模型从任意网页提取摘要"""

    def __init__(self):
        self._crawler: Optional[AsyncWebCrawler] = None

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

    async def extract_async(self, url: str) -> tuple[Optional[str], str]:
        """
        异步提取摘要（需要爬取页面）

        Args:
            url: 论文页面 URL

        Returns:
            (abstract, source) - source 始终为 "origin_llm"
        """
        # LLM 配置
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
        result = await crawler.arun(url=url, config=config)

        if not result.success:
            error_msg = f"Failed to crawl {url}: {result.error_message}"
            print(f"ERROR: {error_msg}")
            raise RuntimeError(error_msg)

        abstract = self._parse_llm_result(result.extracted_content)
        if abstract:
            print(f"OK: origin_llm extracted ({len(abstract)} chars)")
            return abstract, "origin_llm"

        return None, "origin_llm"

    def extract(self, html: str) -> Optional[str]:
        """从 HTML 提取摘要（LLM 提取器不支持同步提取，需调用 extract_async）"""
        raise NotImplementedError("LLMExtractor requires async extraction. Use extract_async() instead.")

    def _parse_llm_result(self, content: Optional[str]) -> Optional[str]:
        """解析 LLM 提取结果"""
        if not content:
            return None

        try:
            data = json.loads(content)

            # 检查 JSON 中是否有 error 字段且为 true
            has_error = False
            if isinstance(data, list) and data:
                has_error = data[0].get('error', False) is True
            elif isinstance(data, dict):
                has_error = data.get('error', False) is True

            if has_error:
                print(f"ERROR: LLM extraction error: {content}")
                return None

            # 提取摘要内容
            abstract = None
            if isinstance(data, list) and data:
                content = data[0].get('content')
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
                return abstract.strip()

        except (json.JSONDecodeError, AttributeError):
            # 直接返回文本内容
            if content and len(content) > 20:
                return content.strip()

        return None


# 全局单例（延迟初始化）
_llm_extractor: Optional[LLMExtractor] = None


def get_llm_extractor() -> LLMExtractor:
    """获取 LLM 提取器单例"""
    global _llm_extractor
    if _llm_extractor is None:
        _llm_extractor = LLMExtractor()
    return _llm_extractor


async def close_llm_extractor():
    """关闭 LLM 提取器"""
    global _llm_extractor
    if _llm_extractor:
        await _llm_extractor.close()
        _llm_extractor = None
