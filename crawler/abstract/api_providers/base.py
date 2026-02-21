"""API 提供者基类"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseAPIClient(ABC):
    """API 客户端基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """API 提供者名称"""
        raise NotImplementedError

    @abstractmethod
    def get_abstract(self, doi: str) -> Optional[str]:
        """通过 DOI 获取摘要"""
        raise NotImplementedError

    @abstractmethod
    def search_by_title(self, title: str) -> Optional[str]:
        """通过标题搜索获取摘要"""
        raise NotImplementedError

    @abstractmethod
    def get_abstract_arxiv(self, arxiv_id: str) -> Optional[str]:
        """通过 arXiv ID 获取摘要"""
        raise NotImplementedError
