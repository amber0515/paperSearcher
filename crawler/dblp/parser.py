"""
HTML 解析模块

提供从 DBLP HTML 页面中提取论文信息的功能。
支持多种解析策略，便于扩展和维护。
"""
import re
from typing import List, Dict, Optional, Callable
from bs4 import BeautifulSoup, Tag
from abc import ABC, abstractmethod

from .models import Paper


# ============================================================
# 解析器策略接口
# ============================================================

class EntryParser(ABC):
    """论文条目解析器接口"""

    @abstractmethod
    def can_parse(self, entry: Tag) -> bool:
        """判断是否可以解析该条目"""
        pass

    @abstractmethod
    def extract_title(self, entry: Tag) -> Optional[str]:
        """提取标题"""
        pass

    def extract_href(self, entry: Tag) -> str:
        """提取链接"""
        link = entry.find('a', href=re.compile(r'/rec/'))
        if link:
            href = link.get('href', '')
            if href and not href.startswith('http'):
                href = 'https://dblp.uni-trier.de' + href
            return href
        return ''

    def extract_authors(self, entry: Tag) -> str:
        """提取作者"""
        author_links = entry.find_all('a', href=re.compile(r'/pid/'))
        author_names = [a.get_text(strip=True) for a in author_links]
        return ', '.join(author_names) if author_names else ''


class StandardParser(EntryParser):
    """标准 DBLP 解析器：处理 <span class="title"> 格式"""

    def can_parse(self, entry: Tag) -> bool:
        return entry.find('span', class_='title') is not None

    def extract_title(self, entry: Tag) -> Optional[str]:
        title_elem = entry.find('span', class_='title')
        if title_elem:
            return title_elem.get_text(strip=True)
        return None


class LinkParser(EntryParser):
    """链接解析器：从论文链接的文本中提取标题"""

    def can_parse(self, entry: Tag) -> bool:
        link = entry.find('a', href=re.compile(r'/rec/conf/[^/]+/\d+'))
        return link is not None and len(link.get_text(strip=True)) > 15

    def extract_title(self, entry: Tag) -> Optional[str]:
        link = entry.find('a', href=re.compile(r'/rec/'))
        if link:
            title = link.get_text(strip=True)
            if len(title) > 15:
                return title
        return None


class DataTitleParser(EntryParser):
    """data-title 属性解析器：处理 <span data-title="..."> 格式"""

    def can_parse(self, entry: Tag) -> bool:
        return entry.find(attrs={'data-title': True}) is not None

    def extract_title(self, entry: Tag) -> Optional[str]:
        elem = entry.find(attrs={'data-title': True})
        if elem:
            return elem.get('data-title', '').strip()
        return None


# ============================================================
# 解析器配置
# ============================================================

# 默认解析器链（按优先级顺序）
DEFAULT_PARSERS: List[EntryParser] = [
    StandardParser(),      # 优先使用标准格式
    DataTitleParser(),     # 尝试 data-title 属性
    LinkParser(),          # 最后尝试链接文本
]


# ============================================================
# 标题过滤
# ============================================================

def should_skip_title(title: str) -> tuple[bool, str]:
    """
    判断是否应该跳过该标题

    Returns:
        tuple[bool, str]: (是否跳过, 原因)
    """
    skip_keywords = [
        'Front Matter', 'Preface', 'Foreword',
        'Contents', 'Program Committee', 'Reviewers', 'Index',
        'keynote', 'invited', 'tutorial', 'panel'
    ]

    title_lower = title.lower()
    for keyword in skip_keywords:
        if keyword.lower() in title_lower:
            return True, f"包含关键词: {keyword}"

    if len(title) < 15:
        return True, f"标题过短 ({len(title)} 字符)"

    if re.match(r'^[\d\s\-\.]+$', title):
        return True, "仅包含数字/特殊字符"

    return False, ""


# ============================================================
# 主解析函数
# ============================================================

def extract_papers_from_html(
    html: str,
    conference: str,
    year: int,
    verbose: bool = False
) -> List[Dict]:
    """
    从 HTML 中提取论文信息

    Args:
        html: DBLP 页面 HTML
        conference: 会议代码
        year: 年份
        verbose: 是否显示详细调试信息

    Returns:
        List[Dict]: 论文列表
    """
    soup = BeautifulSoup(html, 'html.parser')
    entries = _find_entries(soup)

    if verbose:
        print(f"\n  📋 找到 {len(entries)} 个列表项")

    papers = []
    skipped = []
    seen_titles = set()

    for entry in entries:
        title, href, authors = _parse_entry(entry, DEFAULT_PARSERS, conference, year)

        if not title:
            continue

        skip, reason = should_skip_title(title)
        if skip:
            if verbose:
                skipped.append({'title': title, 'reason': reason})
            continue

        if title in seen_titles:
            if verbose:
                skipped.append({'title': title, 'reason': '重复标题'})
            continue
        seen_titles.add(title)

        papers.append({
            'title': title,
            'year': year,
            'conference': conference.upper(),
            'authors': authors,
            'href': href,
            'bib': '',
            'origin': '',
            'abstract': None,
        })

    if verbose:
        print(f"\n  📊 解析结果: {len(papers)} 篇论文, {len(skipped)} 条跳过")
        if skipped:
            print(f"\n  🔍 跳过的条目 (前10条):")
            for i, item in enumerate(skipped[:10], 1):
                print(f"    [{i}] \"{item['title'][:50]}...\" - {item['reason']}")
            if len(skipped) > 10:
                print(f"    ... 还有 {len(skipped) - 10} 条")

    return papers


def _find_entries(soup: BeautifulSoup) -> List[Tag]:
    """查找论文条目"""
    # 优先查找标准格式
    entries = soup.find_all('li', class_=re.compile(r'entry|inproceedings'))
    if entries:
        return entries

    # 回退到所有 li 元素
    return soup.find_all('li')


def _parse_entry(
    entry: Tag,
    parsers: List[EntryParser],
    conference: str,
    year: int
) -> tuple[Optional[str], str, str]:
    """
    使用解析器链解析单个条目

    Returns:
        tuple: (标题, 链接, 作者)
    """
    for parser in parsers:
        if parser.can_parse(entry):
            title = parser.extract_title(entry)
            href = parser.extract_href(entry)
            authors = parser.extract_authors(entry)
            return title, href, authors

    return None, '', ''


# ============================================================
# 向后兼容的旧接口
# ============================================================

def _should_skip(title: str) -> bool:
    """向后兼容：判断是否应该跳过该条目"""
    skip, _ = should_skip_title(title)
    return skip
