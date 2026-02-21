"""
共享数据库操作模块

提供通用的论文和 CCF 场馆数据库操作功能。
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

# 导入配置
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import PAPERS_TABLE


# Default database path
DEFAULT_DB = Path(__file__).parent.parent.parent / "papers.db"
DEFAULT_TEST_DB = Path(__file__).parent.parent.parent / "papers_test.db"


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
        limit: 返回数量限制 (0 或 None 表示无限制)
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

    query = f"""
        SELECT id, title, href, origin, abstract
        FROM {PAPERS_TABLE}
        WHERE (abstract IS NULL OR abstract = '' OR abstract = 'N/A')
    """
    params = []

    if conference:
        query += " AND conference = ?"
        params.append(conference.upper())

    if year:
        query += " AND year = ?"
        params.append(year)

    if limit:
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
        limit: 返回数量限制 (0 或 None 表示无限制)
        conference: 会议筛选
        year: 年份筛选
        has_doi: 是否只返回有 DOI 的论文

    Returns:
        论文列表
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f"""
        SELECT id, title, href, origin, abstract
        FROM {PAPERS_TABLE}
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

    if limit:
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
            f"UPDATE {PAPERS_TABLE} SET abstract = ? WHERE id = ?",
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
        f"SELECT id, title, href, origin, abstract FROM {PAPERS_TABLE} WHERE id = ?",
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


# ==================== DBLP 论文操作 ====================

class Stats:
    """爬取统计信息"""
    def __init__(self):
        self.added = 0
        self.skipped = 0
        self.errors = 0


def save_papers_to_db(papers: List[Dict], db_path: str) -> Stats:
    """
    保存论文到数据库

    Args:
        papers: 论文列表
        db_path: 数据库路径

    Returns:
        Stats: 统计信息（新增、跳过、错误数量）
    """
    stats = Stats()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for paper in papers:
        try:
            # 检查是否已存在
            cursor.execute(
                f"SELECT id FROM {PAPERS_TABLE} WHERE title = ? AND conference = ? AND year = ?",
                (paper['title'], paper['conference'], paper['year'])
            )
            if cursor.fetchone():
                stats.skipped += 1
                continue

            # 插入新论文
            cursor.execute(f"""
                INSERT INTO {PAPERS_TABLE} (conference, year, title, href, origin, bib, abstract)
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


# ==================== CCF 场馆操作 ====================

def init_ccf_venues_table(db_path: str) -> None:
    """初始化 ccf_venues 表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ccf_venues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            abbreviation TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            publisher TEXT,
            ccf_rank TEXT NOT NULL,
            venue_type TEXT NOT NULL,
            domain TEXT NOT NULL,
            dblp_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccf_abbreviation ON ccf_venues(abbreviation)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccf_rank ON ccf_venues(ccf_rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccf_type ON ccf_venues(venue_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ccf_domain ON ccf_venues(domain)")

    conn.commit()
    conn.close()


def save_ccf_venues(venues: List[Dict], db_path: str = None) -> Dict:
    """
    保存 CCF 场馆到数据库

    Args:
        venues: 场馆列表
        db_path: 数据库路径

    Returns:
        统计信息 {'added': int, 'updated': int, 'errors': int}
    """
    if db_path is None:
        db_path = str(DEFAULT_DB)

    stats = {'added': 0, 'updated': 0, 'errors': 0}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 确保表存在
    init_ccf_venues_table(db_path)

    for venue in venues:
        try:
            cursor.execute(
                "SELECT id FROM ccf_venues WHERE abbreviation = ?",
                (venue['abbreviation'],)
            )

            if cursor.fetchone():
                cursor.execute("""
                    UPDATE ccf_venues
                    SET full_name = ?, publisher = ?, ccf_rank = ?,
                        venue_type = ?, domain = ?, dblp_url = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE abbreviation = ?
                """, (
                    venue['full_name'], venue['publisher'], venue['ccf_rank'],
                    venue['venue_type'], venue['domain'], venue.get('dblp_url'),
                    venue['abbreviation']
                ))
                stats['updated'] += 1
            else:
                cursor.execute("""
                    INSERT INTO ccf_venues
                    (abbreviation, full_name, publisher, ccf_rank, venue_type, domain, dblp_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    venue['abbreviation'], venue['full_name'], venue['publisher'],
                    venue['ccf_rank'], venue['venue_type'], venue['domain'],
                    venue.get('dblp_url')
                ))
                stats['added'] += 1

        except Exception as e:
            print(f"Error saving venue {venue.get('abbreviation')}: {e}")
            stats['errors'] += 1

    conn.commit()
    conn.close()

    return stats


def get_ccf_rank(db_path: str, abbreviation: str) -> Optional[str]:
    """获取 CCF 等级"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT ccf_rank FROM ccf_venues WHERE abbreviation = ?", (abbreviation,))
    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def get_venue_info(db_path: str, abbreviation: str) -> Optional[Dict]:
    """获取场馆详细信息"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, abbreviation, full_name, publisher, ccf_rank, venue_type, domain, dblp_url
        FROM ccf_venues WHERE abbreviation = ?
    """, (abbreviation,))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            'id': result[0],
            'abbreviation': result[1],
            'full_name': result[2],
            'publisher': result[3],
            'ccf_rank': result[4],
            'venue_type': result[5],
            'domain': result[6],
            'dblp_url': result[7]
        }
    return None


def get_ccf_statistics(db_path: str = None) -> Dict:
    """获取 CCF 场馆统计信息"""
    if db_path is None:
        db_path = str(DEFAULT_DB)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM ccf_venues")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT ccf_rank, COUNT(*) FROM ccf_venues GROUP BY ccf_rank ORDER BY ccf_rank")
    by_rank = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT venue_type, COUNT(*) FROM ccf_venues GROUP BY venue_type")
    by_type = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("SELECT domain, COUNT(*) FROM ccf_venues GROUP BY domain ORDER BY domain")
    by_domain = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        'total': total,
        'by_rank': by_rank,
        'by_type': by_type,
        'by_domain': by_domain
    }
