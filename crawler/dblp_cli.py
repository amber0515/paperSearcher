#!/usr/bin/env python3
"""
基于 CCF 数据的 DBLP 论文爬虫 CLI

MVP 版本：支持按会议和年份爬取论文

使用示例:
    python -m crawler.dblp_cli CCS 2024
    python -m crawler.dblp_cli CCS,SP,USS 2024
    python -m crawler.dblp_cli --rank A --domain NIS 2024
"""
import argparse
import asyncio
import re
import sqlite3
import sys
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 延迟导入配置（避免导入错误影响帮助显示）
DEFAULT_TEST_DB = Path(__file__).parent.parent / "papers_test.db"


def get_conferences_from_ccf(
    db_path: str,
    rank: str = None,
    domain: str = None,
    venue_type: str = 'conference'
) -> List[Dict]:
    """
    从 CCF 数据库获取会议列表

    Args:
        db_path: 数据库路径
        rank: CCF 等级筛选 (A/B/C)
        domain: 领域筛选 (AI/NIS/CN/...)
        venue_type: 类型筛选 (conference/journal)

    Returns:
        List[Dict]: 会议列表
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT abbreviation, full_name, ccf_rank, venue_type, domain, dblp_url
        FROM ccf_venues
        WHERE 1=1
    """
    params = []

    if venue_type:
        query += " AND venue_type = ?"
        params.append(venue_type)

    if rank:
        query += " AND ccf_rank = ?"
        params.append(rank.upper())

    if domain:
        query += " AND domain = ?"
        params.append(domain.upper())

    query += " ORDER BY abbreviation"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'abbreviation': row[0],
            'full_name': row[1],
            'ccf_rank': row[2],
            'venue_type': row[3],
            'domain': row[4],
            'dblp_url': row[5]
        }
        for row in rows
    ]


def build_year_url(dblp_url: str, year: int) -> str:
    """
    从 DBLP 基础 URL 构建年份特定 URL

    Args:
        dblp_url: DBLP 基础 URL (如 https://dblp.uni-trier.de/db/conf/ccs/)
        year: 年份

    Returns:
        str: 年份特定的 URL
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


async def fetch_papers_async(url: str) -> str:
    """异步获取页面 HTML"""
    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            return result.html
        else:
            raise Exception(f"Failed to fetch {url}: {result.error_message}")


def fetch_papers(url: str) -> str:
    """同步包装"""
    return asyncio.run(fetch_papers_async(url))


def extract_papers_from_html(html: str, conference: str, year: int) -> List[Dict]:
    """
    从 HTML 中提取论文信息

    Args:
        html: DBLP 页面 HTML
        conference: 会议代码
        year: 年份

    Returns:
        List[Dict]: 论文列表
    """
    papers = []
    soup = BeautifulSoup(html, 'html.parser')

    # 查找论文链接（指向 /rec/conf/ 的链接）
    paper_links = soup.find_all('a', href=re.compile(r'/rec/conf/[^/]+/[^/]+\.html'))

    seen_titles = set()

    for link in paper_links:
        href = link.get('href', '')
        title = link.get_text(strip=True)

        # 跳过非论文条目
        if _should_skip(title):
            continue

        # 避免重复
        if title in seen_titles:
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
            'origin': url,
            'abstract': None,
        })

    return papers


def _should_skip(title: str) -> bool:
    """判断是否应该跳过该条目"""
    skip_keywords = [
        'Front Matter', 'Preface', 'Foreword', 'Introduction',
        'Contents', 'Program Committee', 'Reviewers', 'Index',
        'Abstract', 'Presentation', 'Session', 'keynote',
        'invited', 'tutorial', 'panel'
    ]

    title_lower = title.lower()
    for keyword in skip_keywords:
        if keyword.lower() in title_lower:
            return True

    # 跳过过短的标题
    if len(title) < 15:
        return True

    # 跳过纯数字或特殊字符
    if re.match(r'^[\d\s\-\.]+$', title):
        return True

    return False


def save_papers_to_db(papers: List[Dict], db_path: str) -> Dict:
    """
    保存论文到数据库

    Args:
        papers: 论文列表
        db_path: 数据库路径

    Returns:
        Dict: 统计信息
    """
    stats = {'added': 0, 'skipped': 0, 'errors': 0}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for paper in papers:
        try:
            # 检查是否已存在
            cursor.execute(
                "SELECT id FROM papers WHERE title = ? AND conference = ? AND year = ?",
                (paper['title'], paper['conference'], paper['year'])
            )
            if cursor.fetchone():
                stats['skipped'] += 1
                continue

            # 插入新论文
            cursor.execute("""
                INSERT INTO papers (conference, year, title, href, origin, bib, abstract)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                paper['conference'],
                paper['year'],
                paper['title'],
                paper.get('href', ''),
                paper.get('origin', ''),
                paper.get('bib', ''),
                paper.get('abstract')
            ))
            stats['added'] += 1

        except Exception as e:
            print(f"Error saving paper: {e}")
            stats['errors'] += 1

    conn.commit()
    conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='基于 CCF 数据的 DBLP 论文爬虫',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python -m crawler.dblp_cli CCS 2024
  python -m crawler.dblp_cli CCS,SP,USS 2024
  python -m crawler.dblp_cli CCS 2022,2023,2024
  python -m crawler.dblp_cli --rank A --domain NIS 2024
        '''
    )

    parser.add_argument(
        'conferences',
        nargs='?',
        help='会议代码，多个用逗号分隔 (如 CCS,SP,USS)'
    )
    parser.add_argument(
        'years',
        help='年份，多个用逗号分隔 (如 2022,2023,2024)'
    )
    parser.add_argument(
        '--rank',
        choices=['A', 'B', 'C'],
        help='按 CCF 排名筛选 (A/B/C)'
    )
    parser.add_argument(
        '--domain',
        help='按领域筛选 (AI/NIS/CN/SE/DB/...)'
    )
    parser.add_argument(
        '--db',
        default=str(DEFAULT_TEST_DB),
        help=f'数据库路径 (默认: {DEFAULT_TEST_DB})'
    )
    parser.add_argument(
        '--preview-only',
        action='store_true',
        help='仅预览，不保存到数据库'
    )

    args = parser.parse_args()

    # 检查依赖
    try:
        from bs4 import BeautifulSoup
        from crawl4ai import AsyncWebCrawler
    except ImportError as e:
        print("错误: 缺少必要的依赖")
        print(f"  {e}")
        print("\n请安装依赖:")
        print("  pip install crawl4ai beautifulsoup4")
        return 1

    # 验证参数
    if not args.conferences and not args.rank:
        parser.error('请提供会议代码或使用 --rank/--domain 筛选')

    # 解析年份
    years = [int(y.strip()) for y in args.years.split(',')]

    print("=" * 60)
    print("基于 CCF 数据的 DBLP 论文爬虫")
    print(f"数据库: {args.db}")
    print("=" * 60)

    # 获取会议列表
    if args.conferences:
        # 指定了具体会议
        conf_list = [c.strip().upper() for c in args.conferences.split(',')]
        conferences = []
        for conf in conf_list:
            venues = get_conferences_from_ccf(args.db, venue_type='conference')
            venue = next((v for v in venues if v['abbreviation'] == conf), None)
            if venue:
                conferences.append(venue)
            else:
                print(f"警告: 未找到会议 {conf}")
    else:
        # 使用筛选条件
        conferences = get_conferences_from_ccf(
            args.db,
            rank=args.rank,
            domain=args.domain,
            venue_type='conference'
        )
        print(f"找到 {len(conferences)} 个符合条件的会议")

    if not conferences:
        print("错误: 未找到任何会议")
        return 1

    # 爬取论文
    total_stats = {'added': 0, 'skipped': 0, 'errors': 0}

    for venue in conferences:
        conf = venue['abbreviation']
        for year in years:
            print(f"\n[{conf} {year}]")

            # 构建 URL
            url = build_year_url(venue['dblp_url'], year)
            if not url:
                print(f"  错误: 无法构建 URL (dblp_url: {venue['dblp_url']})")
                continue

            print(f"  URL: {url}")

            try:
                # 获取页面
                html = fetch_papers(url)
                print(f"  获取到 {len(html):,} 字符")

                # 提取论文
                papers = extract_papers_from_html(html, conf, year)
                print(f"  找到 {len(papers)} 篇论文")

                if not papers:
                    continue

                # 预览前 3 篇
                for i, p in enumerate(papers[:3], 1):
                    print(f"    {i}. {p['title'][:60]}...")

                if args.preview_only:
                    continue

                # 保存到数据库
                stats = save_papers_to_db(papers, args.db)
                print(f"  新增: {stats['added']}, 跳过: {stats['skipped']}, 错误: {stats['errors']}")

                total_stats['added'] += stats['added']
                total_stats['skipped'] += stats['skipped']
                total_stats['errors'] += stats['errors']

            except Exception as e:
                print(f"  错误: {e}")
                total_stats['errors'] += 1

    print("\n" + "=" * 60)
    print("完成!")
    print(f"总计 - 新增: {total_stats['added']}, 跳过: {total_stats['skipped']}, 错误: {total_stats['errors']}")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
