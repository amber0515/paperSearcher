"""
DBLP 论文爬虫模块

提供从 DBLP 爬取论文数据的功能，包括：
- URL 构建
- 网页获取
- HTML 解析
- 数据库操作
"""

from .models import Paper, Venue, Stats
from .url_builder import build_year_url, build_year_url_all
from .fetcher import fetch_papers, fetch_all_successful_urls
from .parser import extract_papers_from_html
from .database import get_conferences_from_ccf, save_papers_to_db

__all__ = [
    'Paper',
    'Venue',
    'Stats',
    'build_year_url',
    'build_year_url_all',
    'fetch_papers',
    'fetch_all_successful_urls',
    'extract_papers_from_html',
    'get_conferences_from_ccf',
    'save_papers_to_db',
]
