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


async def _fetch_with_fallback_async(urls: list[str]) -> tuple[str, str]:
    """
    异步尝试多个 URL，直到成功

    Args:
        urls: URL 列表（按优先级排序）

    Returns:
        tuple[str, str]: (成功的 URL, HTML 内容)

    Raises:
        Exception: 当所有 URL 都失败时
    """
    errors = []
    for url in urls:
        try:
            html = await _fetch_papers_async(url)
            return url, html
        except Exception as e:
            errors.append(f"{url}: {str(e)}")
            continue

    raise Exception(f"All URLs failed: {'; '.join(errors)}")


def fetch_papers_with_fallback(urls: list[str]) -> tuple[str, str]:
    """
    尝试多个 URL 获取页面，支持自动回退

    Args:
        urls: URL 列表（按优先级排序）

    Returns:
        tuple[str, str]: (成功访问的 URL, HTML 内容)

    Raises:
        Exception: 当所有 URL 都失败时

    Examples:
        >>> url, html = fetch_papers_with_fallback([
        ...     "https://dblp.org/db/conf/crypto/iacr2025/crypto2025.html",
        ...     "https://dblp.org/db/conf/crypto/crypto2025.html"
        ... ])
    """
    return asyncio.run(_fetch_with_fallback_async(urls))


async def _fetch_all_urls_async(urls: list[str]) -> list[tuple[str, str]]:
    """
    异步尝试所有 URL，返回所有成功的

    Args:
        urls: URL 列表（按优先级排序）

    Returns:
        list[tuple[str, str]]: [(成功的 URL, HTML 内容), ...]
    """
    results = []
    for url in urls:
        try:
            html = await _fetch_papers_async(url)
            results.append((url, html))
        except Exception:
            continue
    return results


def fetch_all_successful_urls(urls: list[str]) -> list[tuple[str, str]]:
    """
    尝试所有 URL，返回所有成功的

    用于一年多场会议的场景，会爬取所有可访问的场次。

    Args:
        urls: URL 列表（按优先级排序）

    Returns:
        list[tuple[str, str]]: [(成功访问的 URL, HTML 内容), ...]

    Examples:
        >>> results = fetch_all_successful_urls([
        ...     "https://dblp.org/db/conf/crypto/crypto2025a.html",
        ...     "https://dblp.org/db/conf/crypto/crypto2025b.html"
        ... ])
        >>> for url, html in results:
        ...     print(f"Got {len(html)} bytes from {url}")
    """
    return asyncio.run(_fetch_all_urls_async(urls))
