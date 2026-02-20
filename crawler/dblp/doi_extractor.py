"""
DOI 提取模块

从论文的 href 和 origin 字段提取 DOI 或 arXiv ID。
"""
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional


# DOI 正则表达式
DOI_PATTERN = re.compile(
    r'10\.\d{4,}/[^\s<>"{}|\\^`\[\]]+',
    re.IGNORECASE
)

# arXiv ID 正则表达式
ARXIV_PATTERN = re.compile(
    r'arXiv:?(\d{4}\.\d{4,5})(v\d+)?',
    re.IGNORECASE
)


def extract_arxiv_id(text: str) -> Optional[str]:
    """
    从文本中提取 arXiv ID

    支持:
    - https://arxiv.org/abs/1706.03762
    - arXiv:1706.03762
    - 1706.03762

    Args:
        text: URL 或文本

    Returns:
        arXiv ID 字符串或 None
    """
    if not text:
        return None

    text = text.strip()

    # 1. 尝试匹配 arXiv URL 格式
    # https://arxiv.org/abs/1706.03762
    if 'arxiv.org' in text.lower():
        match = re.search(r'arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})', text, re.IGNORECASE)
        if match:
            return match.group(1)

    # 2. 尝试匹配 arXiv:xxx 格式
    match = re.search(r'arXiv:(\d{4}\.\d{4,5})', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # 3. 尝试匹配纯数字 ID
    if '/' not in text and '.' in text and len(text) > 5:
        # 可能是纯 ID，如 1706.03762
        if text.replace('.', '').replace('v', '').isdigit():
            return text

    return None


def extract_doi(text: str) -> str | None:
    """
    从文本中提取 DOI

    支持:
    - https://doi.org/10.xxxx/...
    - https://dx.doi.org/10.xxxx/...
    - 10.xxxx/...
    - URL 中的 query 参数
    - arXiv ID (转换为 DOI 格式)

    Args:
        text: href 或 origin 字段内容

    Returns:
        DOI 字符串或 None
    """
    # 先尝试提取 arXiv ID 并转换为 DOI 格式
    arxiv_id = extract_arxiv_id(text)
    if arxiv_id:
        return f"10.48550/arXiv.{arxiv_id}"
    if not text:
        return None

    text = text.strip()

    # 1. 尝试从 DOI URL 提取
    parsed = urlparse(text)
    if parsed.netloc in ('doi.org', 'dx.doi.org'):
        # 路径即为 DOI
        path = parsed.path.strip('/')
        if path:
            return path

    # 1.5 ACM 特殊处理
    if parsed.netloc in ('dl.acm.org', 'doi.acm.org'):
        path = parsed.path.strip('/')
        if path.startswith('doi/'):
            path = path[4:]  # 移除 "doi/" 前缀
        if path:
            return path

    # 2. 尝试从 query 参数提取
    if parsed.query:
        params = parse_qs(parsed.query)
        if 'doi' in params:
            return params['doi'][0]

    # 3. 尝试从 URL 路径提取（ACM 等）
    if '/doi/' in text.lower():
        match = re.search(r'/doi/(10\.\d{4,}/[^\s?#]+)', text, re.IGNORECASE)
        if match:
            return match.group(1)

    # 4. 尝试正则匹配 DOI 格式
    match = DOI_PATTERN.search(text)
    if match:
        return match.group(0)

    return None


def extract_doi_from_origin(origin: str, href: str = "") -> str | None:
    """
    从 origin 或 href 字段提取 DOI

    优先从 origin 提取，其次 href

    Args:
        origin: 原始网站链接
        href: DBLP 详情页链接

    Returns:
        DOI 字符串或 None
    """
    # 优先从 origin 提取
    doi = extract_doi(origin)
    if doi:
        return doi

    # 其次从 href 提取
    if href:
        doi = extract_doi(href)
        if doi:
            return doi

    return None


if __name__ == '__main__':
    # 测试用例
    test_cases = [
        "https://doi.org/10.1145/3580305.3599234",
        "https://dl.acm.org/doi/10.1145/3580305.3599234",
        "https://www.usenix.org/legacy/events/sec08/tech/",
        "10.1145/3580305.3599234",
        "https://doi.org/10.1007/978-3-031-57255-5_12",
    ]

    for case in test_cases:
        doi = extract_doi(case)
        print(f"{case} -> {doi}")
