"""
通用数据模型定义

定义论文、场馆等数据结构。
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Paper:
    """论文数据模型"""
    title: str
    year: int
    conference: str
    authors: str = ""
    href: str = ""
    bib: str = ""
    origin: str = ""
    abstract: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'year': self.year,
            'conference': self.conference,
            'authors': self.authors,
            'href': self.href,
            'bib': self.bib,
            'origin': self.origin,
            'abstract': self.abstract,
        }

    def to_db_tuple(self) -> tuple:
        return (
            self.conference,
            self.year,
            self.title,
            self.href,
            self.origin,
            self.bib,
            self.abstract,
        )


@dataclass
class Venue:
    """场馆数据模型（CCF 会议/期刊）"""
    abbreviation: str
    full_name: str
    ccf_rank: str
    venue_type: str
    domain: str
    dblp_url: str = ""

    def to_dict(self) -> dict:
        return {
            'abbreviation': self.abbreviation,
            'full_name': self.full_name,
            'ccf_rank': self.ccf_rank,
            'venue_type': self.venue_type,
            'domain': self.domain,
            'dblp_url': self.dblp_url,
        }


@dataclass
class Stats:
    """统计信息数据模型"""
    added: int = 0
    skipped: int = 0
    errors: int = 0

    def __iadd__(self, other: 'Stats') -> 'Stats':
        self.added += other.added
        self.skipped += other.skipped
        self.errors += other.errors
        return self

    def to_dict(self) -> dict:
        return {
            'added': self.added,
            'skipped': self.skipped,
            'errors': self.errors,
        }
