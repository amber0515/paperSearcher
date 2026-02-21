"""API 提供者模块

使用 Semantic Scholar 和 OpenAlex API 获取论文摘要。
"""
from typing import Optional

from .base import BaseAPIClient
from .semantic_scholar import SemanticScholarClient
from .openalex import OpenAlexClient


# 默认客户端实例
_semantic_scholar_client: Optional[SemanticScholarClient] = None
_openalex_client: Optional[OpenAlexClient] = None


def get_semantic_scholar_client() -> SemanticScholarClient:
    """获取 Semantic Scholar 客户端单例"""
    global _semantic_scholar_client
    if _semantic_scholar_client is None:
        _semantic_scholar_client = SemanticScholarClient()
    return _semantic_scholar_client


def get_openalex_client() -> OpenAlexClient:
    """获取 OpenAlex 客户端单例"""
    global _openalex_client
    if _openalex_client is None:
        _openalex_client = OpenAlexClient()
    return _openalex_client


__all__ = [
    "BaseAPIClient",
    "SemanticScholarClient",
    "OpenAlexClient",
    "get_semantic_scholar_client",
    "get_openalex_client",
]
