"""
CCF Metadata Crawler - 使用 Crawl4AI
Fetches conference/journal metadata from CCF official website
"""
import asyncio
from crawl4ai import AsyncWebCrawler
from typing import Dict


# CCF 官网域名
CCF_BASE_URL = "https://www.ccf.org.cn/Academic_Evaluation/"

# 领域代码映射 (CCF 官网 URL 代码)
# 从主页 https://www.ccf.org.cn/Academic_Evaluation/By_category/ 提取
CCF_DOMAIN_CODES = {
    'ARCH': 'ARCH_DCP_SS',           # 计算机体系结构/并行与分布计算/存储系统
    'CN': 'CN',                     # 计算机网络
    'NIS': 'NIS',                   # 网络与信息安全
    'SE': 'TCSE_SS_PDL',            # 软件工程/系统软件/程序设计语言
    'DB': 'DM_CS',                  # 数据库/数据挖掘/内容检索
    'TC': 'TCS',                    # 计算机科学理论
    'GM': 'CGAndMT',                # 计算机图形学与多媒体
    'AI': 'AI',                     # 人工智能
    'HCI': 'HCIAndPC',              # 人机交互与普适计算
    'Cross': 'Cross_Compre_Emerging',  # 交叉/综合/新兴
}

async def fetch_ccf_domain_page_async(domain_code: str) -> str:
    """
    使用 Crawl4AI 获取指定领域页面的 Markdown 内容

    Args:
        domain_code: 领域代码 (如 'CN', 'NIS', 'AI')

    Returns:
        str: Markdown content of the page

    Raises:
        Exception: If the request fails
    """
    url_code = CCF_DOMAIN_CODES[domain_code]
    url = f"{CCF_BASE_URL}{url_code}/"

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            word_count_threshold=10,
            page_timeout=30000,
        )
        if result.success:
            # 使用 markdown 格式，更容易解析
            return result.markdown
        else:
            raise Exception(f"Failed to fetch {url}: {result.error_message}")


def fetch_ccf_domain_page(domain_code: str) -> str:
    """
    同步接口：获取指定领域页面内容

    Args:
        domain_code: 领域代码 (如 'CN', 'NIS', 'AI')

    Returns:
        str: Markdown content of the page
    """
    return asyncio.run(fetch_ccf_domain_page_async(domain_code))


async def fetch_all_ccf_pages_async() -> Dict[str, str]:
    """
    获取所有 CCF 领域页面的内容

    Returns:
        Dict: {domain_code: markdown_content}
    """
    results = {}

    for domain_code in CCF_DOMAIN_CODES.keys():
        try:
            print(f"Fetching {domain_code}...")
            markdown = await fetch_ccf_domain_page_async(domain_code)
            results[domain_code] = markdown
            print(f"  Got {len(markdown):,} characters")
        except Exception as e:
            print(f"  Error: {e}")
            results[domain_code] = None

    return results


def fetch_all_ccf_pages() -> Dict[str, str]:
    """
    同步接口：获取所有 CCF 领域页面的内容

    Returns:
        Dict: {domain_code: markdown_content}
    """
    return asyncio.run(fetch_all_ccf_pages_async())
