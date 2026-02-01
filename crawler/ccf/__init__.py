"""
CCF Metadata Crawler Module

Crawls CCF (China Computer Federation) recommended conference/journal rankings
and stores them in the database.
"""

from .crawler import fetch_ccf_domain_page, fetch_all_ccf_pages
from .parser import parse_ccf_html, parse_all_ccf_pages
from .database import save_ccf_venues, get_ccf_rank, get_venue_info, get_statistics

__all__ = [
    'fetch_ccf_domain_page',
    'fetch_all_ccf_pages',
    'parse_ccf_html',
    'parse_all_ccf_pages',
    'save_ccf_venues',
    'get_ccf_rank',
    'get_venue_info',
    'get_statistics'
]
