"""
网页获取模块
"""
import asyncio
from crawl4ai import AsyncWebCrawler


async def _fetch_papers_async(url: str) -> str:
    """异步获取单个 URL 的 HTML"""
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            return result.html
        else:
            raise Exception(f"Failed to fetch {url}: {result.error_message}")


def fetch_papers(url: str) -> str:
    """同步接口：获取单个 URL"""
    return asyncio.run(_fetch_papers_async(url))


async def _fetch_all_urls_async(urls: list[str]) -> list[tuple[str, str]]:
    """异步尝试所有 URL，返回所有成功的 (URL, HTML)"""
    results = []
    for url in urls:
        try:
            html = await _fetch_papers_async(url)
            results.append((url, html))
        except Exception:
            continue
    return results


def fetch_all_successful_urls(urls: list[str]) -> list[tuple[str, str]]:
    """尝试所有 URL，返回所有成功的"""
    return asyncio.run(_fetch_all_urls_async(urls))
