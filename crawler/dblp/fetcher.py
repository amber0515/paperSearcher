"""
网页获取模块

提供从 DBLP 获取 HTML 页面的功能。
"""
import asyncio
from crawl4ai import AsyncWebCrawler


async def _fetch_papers_async(url: str) -> str:
    """
    异步获取页面 HTML

    Args:
        url: 目标 URL

    Returns:
        str: 页面 HTML 内容

    Raises:
        Exception: 当获取失败时
    """
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            return result.html
        else:
            raise Exception(f"Failed to fetch {url}: {result.error_message}")


def fetch_papers(url: str) -> str:
    """
    获取 DBLP 页面 HTML（同步接口）

    Args:
        url: 目标 URL

    Returns:
        str: 页面 HTML 内容

    Raises:
        Exception: 当获取失败时

    Examples:
        >>> html = fetch_papers("https://dblp.uni-trier.de/db/conf/ccs/ccs2024.html")
    """
    return asyncio.run(_fetch_papers_async(url))
