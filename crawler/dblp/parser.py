"""
HTML 解析模块

提供从 DBLP HTML 页面中提取论文信息的功能。
支持多种解析策略，便于扩展和维护。
"""
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup, Tag
from abc import ABC, abstractmethod
from crawler.shared.models import Paper


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

    def extract_origin(self, entry: Tag) -> str:
        """提取原始会议/期刊网站链接

        从论文条目中提取原始发布网站的链接。
        优先级：
        1. nav.publ > .body > .ee > a (electronic edition)
        2. 外部链接（usenix.org, dl.acm.org, ieeexplore.ieee.org 等）
        """
        nav = entry.find('nav', class_='publ')
        if not nav:
            return ''

        # 方法1: 优先查找 .body 下的 .ee (electronic edition) 链接
        first_dropdown = nav.find('li', class_='drop-down')
        if first_dropdown:
            body = first_dropdown.find('div', class_='body')
            if body:
                ee = body.find('li', class_='ee')
                if ee:
                    link = ee.find('a', href=True)
                    if link:
                        href = link.get('href', '')
                        # 如果是 DOI 链接，继续寻找其他外部链接
                        if 'doi.org' in href:
                            pass  # 继续查找其他链接
                        else:
                            return href

        # 方法2: 查找外部链接（usenix.org, dl.acm.org, ieeexplore.ieee.org 等）
        all_links = entry.find_all('a', href=True)
        external_patterns = [
            r'https?://[^/]*\.usenix\.org/',
            r'https?://dl\.acm\.org/',
            r'https?://ieeexplore\.ieee\.org/',
            r'https?://openaccess\.thecvf\.com/',
            r'https?://papers\.nips\.cc/',
            r'https?://proceedings\.mlr\.press/',
        ]
        for link in all_links:
            href = link.get('href', '')
            for pattern in external_patterns:
                if re.search(pattern, href):
                    return href

        # 方法3: 如果没有外部链接，返回 DOI 链接
        for link in all_links:
            href = link.get('href', '')
            if href.startswith('https://doi.org/'):
                return href

        return ''

    def extract_authors(self, entry: Tag) -> str:
        """提取作者"""
        author_links = entry.find_all('a', href=re.compile(r'/pid/'))
        author_names = [a.get_text(strip=True) for a in author_links]
        return ', '.join(author_names) if author_names else ''


class StandardParser(EntryParser):
    """标准解析器：处理 <span class="title"> 格式"""

    def can_parse(self, entry: Tag) -> bool:
        return entry.find('span', class_='title') is not None

    def extract_title(self, entry: Tag) -> Optional[str]:
        title_elem = entry.find('span', class_='title')
        if title_elem:
            return title_elem.get_text(strip=True)
        return None


class LinkParser(EntryParser):
    """链接解析器：从链接文本中提取标题"""

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
    """data-title 属性解析器"""

    def can_parse(self, entry: Tag) -> bool:
        return entry.find(attrs={'data-title': True}) is not None

    def extract_title(self, entry: Tag) -> Optional[str]:
        elem = entry.find(attrs={'data-title': True})
        if elem:
            return elem.get('data-title', '').strip()
        return None


# 解析器配置
DEFAULT_PARS: List[EntryParser] = [
    StandardParser(),
    DataTitleParser(),
    LinkParser(),
]


def should_skip_title(title: str) -> tuple[bool, str]:
    """判断是否应该跳过该标题"""
    skip_keywords = [
        'Front Matter', 'Preface', 'Foreword', 'Introduction',
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


def _parse_entry(entry: Tag, parsers: List[EntryParser], conference: str, year: int) -> tuple:
    """使用解析器列表解析单个条目"""
    for parser in parsers:
        if parser.can_parse(entry):
            title = parser.extract_title(entry)
            href = parser.extract_href(entry)
            authors = parser.extract_authors(entry)
            origin = parser.extract_origin(entry)
            return title, href, authors, origin
    return None, '', '', ''


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

    # 查找包含论文的列表项（优先使用 entry 类）
    entries = soup.find_all('li', class_=re.compile(r'entry|inproceedings'))

    papers = []
    seen_titles = set()

    for entry in entries:
        title, href, authors, origin = _parse_entry(entry, DEFAULT_PARS, conference, year)

        if not title:
            continue

        skip, reason = should_skip_title(title)
        if skip:
            continue

        if title in seen_titles:
            continue

        seen_titles.add(title)

        papers.append({
            'title': title,
            'year': year,
            'conference': conference.upper(),
            'authors': authors,
            'href': href,
            'bib': '',
            'origin': origin,
            'abstract': None,
        })

    return papers


def _should_skip(title: str) -> bool:
    """向后兼容：判断是否应该跳过该条目"""
    return should_skip_title(title) is not None