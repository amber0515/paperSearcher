"""
基于 Crawl4AI 的论文爬虫

从 DBLP 爬取会议论文列表页面
"""
import asyncio
from crawl4ai import AsyncWebCrawler
from .config import build_dblp_url


async def fetch_papers_from_dblp(conference: str, year: int) -> str:
    """
    使用 Crawl4AI 从 DBLP 爬取论文页面

    Args:
        conference: 会议代码 (如 'CCS', 'SP')
        year: 年份 (如 2024)

    Returns:
        str: DBLP 页面的 HTML 内容

    Raises:
        Exception: 爬取失败时抛出异常
    """
    url = build_dblp_url(conference, year)

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            # 获取 HTML 以便精确解析
        )
        if result.success:
            return result.html
        else:
            raise Exception(f"Failed to fetch {url}: {result.error_message}")


# 同步包装函数（方便调用）
def fetch_papers(conference: str, year: int) -> str:
    """
    同步接口：获取 DBLP 页面的 HTML

    Args:
        conference: 会议代码 (如 'CCS', 'SP')
        year: 年份 (如 2024)

    Returns:
        str: DBLP 页面的 HTML 内容
    """
    return asyncio.run(fetch_papers_from_dblp(conference, year))
