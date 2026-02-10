"""
HTML 解析模块

提供从 DBLP HTML 页面中提取论文信息的功能。
"""
import re
from typing import List, Dict
from bs4 import BeautifulSoup

from .models import Paper


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
    papers = []
    skipped = []
    soup = BeautifulSoup(html, 'html.parser')

    # 查找论文链接（指向 /rec/conf/ 的链接）
    paper_links = soup.find_all('a', href=re.compile(r'/rec/conf/[^/]+/[^/]+\.html'))

    seen_titles = set()

    for link in paper_links:
        href = link.get('href', '')
        title = link.get_text(strip=True)

        # 跳过非论文条目
        skip_reason = _should_skip_verbose(title)
        if skip_reason:
            if verbose:
                skipped.append({'title': title, 'reason': skip_reason})
            continue

        # 避免重复
        if title in seen_titles:
            if verbose:
                skipped.append({'title': title, 'reason': '重复标题'})
            continue
        seen_titles.add(title)

        # 获取作者
        authors = ""
        li_parent = link.find_parent('li')
        if li_parent:
            author_links = li_parent.find_all('a', href=re.compile(r'/pid/'))
            author_names = [a.get_text(strip=True) for a in author_links]
            authors = ', '.join(author_names) if author_names else ""

        # 确保完整 URL
        if href and not href.startswith('http'):
            href = 'https://dblp.uni-trier.de' + href

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

    if verbose and skipped:
        print(f"\n  🔍 跳过的条目 ({len(skipped)} 条):")
        for i, item in enumerate(skipped[:10], 1):  # 最多显示 10 条
            print(f"    [{i}] \"{item['title'][:50]}...\" - {item['reason']}")
        if len(skipped) > 10:
            print(f"    ... 还有 {len(skipped) - 10} 条")

    return papers


def _should_skip(title: str) -> bool:
    """
    判断是否应该跳过该条目

    Args:
        title: 标题文本

    Returns:
        bool: 是否跳过
    """
    return _should_skip_verbose(title) is not None


def _should_skip_verbose(title: str) -> str | None:
    """
    判断是否应该跳过该条目，返回跳过原因

    Args:
        title: 标题文本

    Returns:
        str | None: 跳过原因，如果不跳过则返回 None
    """
    skip_keywords = [
        'Front Matter', 'Preface', 'Foreword', 'Introduction',
        'Contents', 'Program Committee', 'Reviewers', 'Index',
        'Abstract', 'Presentation', 'Session', 'keynote',
        'invited', 'tutorial', 'panel'
    ]

    title_lower = title.lower()
    for keyword in skip_keywords:
        if keyword.lower() in title_lower:
            return f"包含关键词: {keyword}"

    # 跳过过短的标题
    if len(title) < 15:
        return f"标题过短 ({len(title)} 字符)"

    # 跳过纯数字或特殊字符
    if re.match(r'^[\d\s\-\.]+$', title):
        return "仅包含数字/特殊字符"

    return None
