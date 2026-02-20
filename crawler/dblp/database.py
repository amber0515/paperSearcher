"""
数据库操作模块

提供从 CCF 数据库获取会议信息和保存论文数据的功能。
"""
import sqlite3
from typing import List, Dict, Optional

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


def get_papers_without_abstract(
    db_path: str,
    limit: int = 100,
    conference: str = None,
    year: int = None
) -> List[Dict]:
    """
    获取没有摘要的论文

    Args:
        db_path: 数据库路径
        limit: 返回数量限制
        conference: 会议筛选
        year: 年份筛选

    Returns:
        论文列表

    Examples:
        >>> papers = get_papers_without_abstract("papers.db", limit=100)
        >>> len(papers)
        100
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT id, title, href, origin, abstract
        FROM papers
        WHERE (abstract IS NULL OR abstract = '' OR abstract = 'N/A')
    """
    params = []

    if conference:
        query += " AND conference = ?"
        params.append(conference.upper())

    if year:
        query += " AND year = ?"
        params.append(year)

    query += " LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'id': row[0],
            'title': row[1],
            'href': row[2],
            'origin': row[3],
            'abstract': row[4],
        }
        for row in rows
    ]


def get_papers_for_refresh(
    db_path: str,
    limit: int = 100,
    conference: str = None,
    year: int = None,
    has_doi: bool = True
) -> List[Dict]:
    """
    获取需要刷新摘要的论文（用于测试刷新功能）

    Args:
        db_path: 数据库路径
        limit: 返回数量限制
        conference: 会议筛选
        year: 年份筛选
        has_doi: 是否只返回有 DOI 的论文

    Returns:
        论文列表
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = """
        SELECT id, title, href, origin, abstract
        FROM papers
        WHERE 1=1
    """
    params = []

    if has_doi:
        query += " AND (href LIKE '%doi%' OR origin LIKE '%doi%')"

    if conference:
        query += " AND conference = ?"
        params.append(conference.upper())

    if year:
        query += " AND year = ?"
        params.append(year)

    query += " LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            'id': row[0],
            'title': row[1],
            'href': row[2],
            'origin': row[3],
            'abstract': row[4],
        }
        for row in rows
    ]


def update_paper_abstract(
    db_path: str,
    paper_id: int,
    abstract: str,
    source: str
) -> bool:
    """
    更新论文摘要

    Args:
        db_path: 数据库路径
        paper_id: 论文 ID
        abstract: 摘要内容
        source: 来源 (crossref/semantic_scholar/origin)

    Returns:
        是否成功

    Examples:
        >>> success = update_paper_abstract("papers.db", 123, "This paper...", "crossref")
        >>> print(success)
        True
    """
    if not abstract:
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE papers SET abstract = ? WHERE id = ?",
            (abstract, paper_id)
        )
        success = cursor.rowcount > 0
        conn.commit()
    except Exception as e:
        print(f"Error updating abstract for paper {paper_id}: {e}")
        success = False
    finally:
        conn.close()

    return success


def get_paper_by_id(db_path: str, paper_id: int) -> Optional[Dict]:
    """
    根据 ID 获取论文

    Args:
        db_path: 数据库路径
        paper_id: 论文 ID

    Returns:
        论文字典或 None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, href, origin, abstract FROM papers WHERE id = ?",
        (paper_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            'id': row[0],
            'title': row[1],
            'href': row[2],
            'origin': row[3],
            'abstract': row[4],
        }
    return None
