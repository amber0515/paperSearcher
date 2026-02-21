"""
CCF Metadata Crawler Module

Crawls CCF (China Computer Federation) recommended conference/journal rankings.

数据库操作统一放在 shared/database.py
"""

from .fetcher import fetch_ccf_domain_page, fetch_all_ccf_pages
from .parser import parse_ccf_html, parse_all_ccf_pages

__all__ = [
    'fetch_ccf_domain_page',
    'fetch_all_ccf_pages',
    'parse_ccf_html',
    'parse_all_ccf_pages',
]
