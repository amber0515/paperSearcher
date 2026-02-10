"""
URL 构建模块

提供从 DBLP 基础 URL 构建年份特定 URL 的功能。
"""


def build_year_url(dblp_url: str, year: int) -> str | None:
    """
    从 DBLP 基础 URL 构建年份特定 URL

    Args:
        dblp_url: DBLP 基础 URL (如 https://dblp.uni-trier.de/db/conf/ccs/)
        year: 年份

    Returns:
        str | None: 年份特定的 URL，如果输入无效则返回 None

    Examples:
        >>> build_year_url("https://dblp.uni-trier.de/db/conf/ccs/", 2024)
        'https://dblp.uni-trier.de/db/conf/ccs/ccs2024.html'
    """
    if not dblp_url:
        return None

    # 移除末尾的斜杠
    base = dblp_url.rstrip('/')

    # 提取会议代码（最后一个路径部分）
    parts = base.split('/')
    conf_code = parts[-1]

    # 构建年份 URL
    return f"{base}/{conf_code}{year}.html"
