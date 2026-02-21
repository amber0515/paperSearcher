"""
DBLP 论文爬虫模块

提供从 DBLP 爬取论文数据的功能，包括：
- URL 构建
- 网页获取
- HTML 解析

数据库操作和通用模型统一放在 shared/ 目录
"""

from crawler.shared.models import Paper, Venue, Stats
from .url_builder import build_year_url, build_year_url_all
from .fetcher import fetch_papers, fetch_all_successful_urls
from .parser import extract_papers_from_html

__all__ = [
    'Paper',
    'Venue',
    'Stats',
    'build_year_url',
    'build_year_url_all',
    'fetch_papers',
    'fetch_all_successful_urls',
    'extract_papers_from_html',
]
