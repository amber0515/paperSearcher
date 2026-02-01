"""
Database operations for CCF venue metadata
"""

import sqlite3
from pathlib import Path
from typing import List, Dict


# Default test database path
DEFAULT_TEST_DB = Path(__file__).parent.parent.parent / "papers_test.db"


def create_ccf_venues_table(conn: sqlite3.Connection) -> None:
    """
    Create ccf_venues table if it doesn't exist

    Args:
        conn: SQLite connection
    """
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

    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ccf_abbreviation
        ON ccf_venues(abbreviation)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ccf_rank
        ON ccf_venues(ccf_rank)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ccf_type
        ON ccf_venues(venue_type)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ccf_domain
        ON ccf_venues(domain)
    """)

    conn.commit()


def save_ccf_venues(venues: List[Dict], db_path: str = None) -> Dict:
    """
    Save CCF venues to database

    Args:
        venues: List of venue dictionaries
        db_path: Path to SQLite database (default: papers_test.db)

    Returns:
        Dict with statistics: {'added': int, 'updated': int, 'errors': int}
    """
    if db_path is None:
        db_path = str(DEFAULT_TEST_DB)

    stats = {'added': 0, 'updated': 0, 'errors': 0}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure table exists
    create_ccf_venues_table(conn)

    for venue in venues:
        try:
            # Check if exists
            cursor.execute(
                "SELECT id FROM ccf_venues WHERE abbreviation = ?",
                (venue['abbreviation'],)
            )

            if cursor.fetchone():
                # Update existing
                cursor.execute("""
                    UPDATE ccf_venues
                    SET full_name = ?,
                        publisher = ?,
                        ccf_rank = ?,
                        venue_type = ?,
                        domain = ?,
                        dblp_url = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE abbreviation = ?
                """, (
                    venue['full_name'],
                    venue['publisher'],
                    venue['ccf_rank'],
                    venue['venue_type'],
                    venue['domain'],
                    venue.get('dblp_url'),
                    venue['abbreviation']
                ))
                stats['updated'] += 1
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO ccf_venues
                    (abbreviation, full_name, publisher, ccf_rank, venue_type, domain, dblp_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    venue['abbreviation'],
                    venue['full_name'],
                    venue['publisher'],
                    venue['ccf_rank'],
                    venue['venue_type'],
                    venue['domain'],
                    venue.get('dblp_url')
                ))
                stats['added'] += 1

        except Exception as e:
            print(f"Error saving venue {venue.get('abbreviation')}: {e}")
            stats['errors'] += 1

    conn.commit()
    conn.close()

    return stats


def get_ccf_rank(db_path: str, abbreviation: str) -> str | None:
    """
    Get CCF rank for a venue abbreviation

    Args:
        db_path: Database path
        abbreviation: Venue abbreviation (e.g., 'CCS')

    Returns:
        str: CCF rank ('A', 'B', 'C') or None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT ccf_rank FROM ccf_venues WHERE abbreviation = ?",
        (abbreviation,)
    )

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None


def get_venue_info(db_path: str, abbreviation: str) -> dict | None:
    """
    Get full venue information

    Args:
        db_path: Database path
        abbreviation: Venue abbreviation

    Returns:
        Dict with venue info or None
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, abbreviation, full_name, publisher, ccf_rank,
                  venue_type, domain, dblp_url
           FROM ccf_venues WHERE abbreviation = ?""",
        (abbreviation,)
    )

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


def get_statistics(db_path: str = None) -> Dict:
    """
    Get statistics about CCF venues in database

    Args:
        db_path: Database path

    Returns:
        Dict with statistics
    """
    if db_path is None:
        db_path = str(DEFAULT_TEST_DB)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM ccf_venues")
    total = cursor.fetchone()[0]

    # By rank
    cursor.execute("""
        SELECT ccf_rank, COUNT(*)
        FROM ccf_venues
        GROUP BY ccf_rank
        ORDER BY ccf_rank
    """)
    by_rank = {row[0]: row[1] for row in cursor.fetchall()}

    # By type
    cursor.execute("""
        SELECT venue_type, COUNT(*)
        FROM ccf_venues
        GROUP BY venue_type
    """)
    by_type = {row[0]: row[1] for row in cursor.fetchall()}

    # By domain
    cursor.execute("""
        SELECT domain, COUNT(*)
        FROM ccf_venues
        GROUP BY domain
        ORDER BY domain
    """)
    by_domain = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        'total': total,
        'by_rank': by_rank,
        'by_type': by_type,
        'by_domain': by_domain
    }
