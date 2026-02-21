"""
数据库操作模块

提供从 CCF 数据库获取会议信息和保存论文数据的功能。
"""
import sqlite3
from typing import List, Dict

from .models import Stats, Venue


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

    Examples:
        >>> venues = get_conferences_from_ccf("papers.db", rank="A", domain="NIS")
        >>> len(venues)
        5
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


def save_papers_to_db(papers: List[Dict], db_path: str) -> Stats:
    """
    保存论文到数据库

    Args:
        papers: 论文列表
        db_path: 数据库路径

    Returns:
        Stats: 统计信息（新增、跳过、错误数量）

    Examples:
        >>> stats = save_papers_to_db(papers, "papers.db")
        >>> print(f"新增: {stats.added}, 跳过: {stats.skipped}")
    """
    stats = Stats()

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
                stats.skipped += 1
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
            stats.added += 1

        except Exception as e:
            print(f"Error saving paper: {e}")
            stats.errors += 1

    conn.commit()
    conn.close()

    return stats
