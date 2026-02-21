"""API 提供者模块

可扩展的 API 客户端，按优先级尝试各个 API 获取摘要。
"""
from typing import Optional, Type

from .base import BaseAPIClient
from .crossref import CrossrefClient
from .openalex import OpenAlexClient
from .semantic_scholar import SemanticScholarClient


# API 提供者注册表（按优先级顺序）
API_PROVIDERS: list[Type[BaseAPIClient]] = [
    CrossrefClient,
    OpenAlexClient,
    SemanticScholarClient,
]


def get_api_provider(name: str) -> Optional[BaseAPIClient]:
    """根据名称获取 API 提供者实例"""
    for provider_cls in API_PROVIDERS:
        if provider_cls().name == name.lower():
            return provider_cls()
    return None


# 默认客户端实例
_crossref_client: Optional[CrossrefClient] = None
_openalex_client: Optional[OpenAlexClient] = None
_semantic_scholar_client: Optional[SemanticScholarClient] = None


def get_crossref_client() -> CrossrefClient:
    """获取 Crossref 客户端单例"""
    global _crossref_client
    if _crossref_client is None:
        _crossref_client = CrossrefClient()
    return _crossref_client


def get_openalex_client() -> OpenAlexClient:
    """获取 OpenAlex 客户端单例"""
    global _openalex_client
    if _openalex_client is None:
        _openalex_client = OpenAlexClient()
    return _openalex_client


def get_semantic_scholar_client() -> SemanticScholarClient:
    """获取 Semantic Scholar 客户端单例"""
    global _semantic_scholar_client
    if _semantic_scholar_client is None:
        _semantic_scholar_client = SemanticScholarClient()
    return _semantic_scholar_client


__all__ = [
    "BaseAPIClient",
    "CrossrefClient",
    "OpenAlexClient",
    "SemanticScholarClient",
    "API_PROVIDERS",
    "get_api_provider",
    "get_crossref_client",
    "get_openalex_client",
    "get_semantic_scholar_client",
]
