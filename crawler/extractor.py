"""
从 HTML 中提取论文信息

使用 BeautifulSoup 解析 DBLP 页面 HTML
"""
import re
from typing import List, Dict
from bs4 import BeautifulSoup
from .config import build_dblp_url, normalize_conference


def extract_papers_from_markdown(
    html: str,
    conference: str,
    year: int
) -> List[Dict]:
    """
    从 DBLP 的 HTML 中提取论文信息

    Args:
        html: DBLP 页面的 HTML 内容
        conference: 会议代码
        year: 年份

    Returns:
        List[Dict]: 论文列表，每个论文包含 title, authors, href, bib 等
    """
    papers = []
    conf_normalized = normalize_conference(conference)
    soup = BeautifulSoup(html, 'html.parser')

    # DBLP 的论文条目通常在 <li> 标签中，包含指向论文详情的链接
    # 查找所有包含论文链接的 <li> 元素
    # 论文链接通常指向 dblp.org/rec/conf/

    # 查找所有指向论文记录的链接（包含 /rec/conf/）
    paper_links = soup.find_all('a', href=re.compile(r'/rec/conf/[^/]+/[^/]+\.html'))

    seen_titles = set()

    for link in paper_links:
        href = link.get('href', '')
        title = link.get_text(strip=True)

        # 跳过非论文条目
        if _skip_entry(title):
            continue

        # 避免重复
        if title in seen_titles:
            continue
        seen_titles.add(title)

        # 获取作者信息 - 通常是同个 li 元素中其他链接
        authors = ""
        li_parent = link.find_parent('li')
        if li_parent:
            # 查找作者链接（通常是 pid/ 链接）
            author_links = li_parent.find_all('a', href=re.compile(r'/pid/'))
            author_names = [a.get_text(strip=True) for a in author_links]
            authors = ', '.join(author_names) if author_names else ""

        # 获取 BibTeX 链接
        bib = ""
        if li_parent:
            bib_link = li_parent.find('a', text=re.compile(r'BibTeX', re.IGNORECASE))
            if bib_link:
                bib = bib_link.get('href', '')

        # 确保 href 是完整 URL
        if href and not href.startswith('http'):
            href = 'https://dblp.uni-trier.de' + href

        # 确保 bib 是完整 URL
        if bib and not bib.startswith('http'):
            bib = 'https://dblp.uni-trier.de' + bib

        papers.append({
            'title': title,
            'year': year,
            'conference': conf_normalized,
            'authors': authors,
            'href': href,
            'bib': bib,
            'origin': build_dblp_url(conference, year),
            'abstract': None,  # 摘要需要单独获取
        })

    return papers


def _skip_entry(title: str) -> bool:
    """
    判断是否应该跳过该条目（非论文条目）

    Args:
        title: 条目标题

    Returns:
        bool: True 表示应该跳过
    """
    skip_keywords = [
        'Front Matter',
        'Preface',
        'Foreword',
        'Introduction',
        'Contents',
        'Program Committee',
        'Reviewers',
        'Index',
        'Abstract',
        'Presentation',
        'Session',
        'keynote',
        'invited',
        'tutorial',
        'panel',
    ]

    title_lower = title.lower()
    for keyword in skip_keywords:
        if keyword.lower() in title_lower:
            return True

    # 跳过过短的标题（可能是噪音）
    if len(title) < 15:
        return True

    # 跳过纯数字或特殊字符的标题
    if re.match(r'^[\d\s\-\.]+$', title):
        return True

    return False
