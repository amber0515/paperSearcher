"""提取器基类"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseExtractor(ABC):
    """提取器基类"""

    @abstractmethod
    def extract(self, html: str) -> Optional[str]:
        """从 HTML 中提取摘要

        Args:
            html: 网页 HTML 内容

        Returns:
            提取的摘要文本，提取失败返回 None
        """
        raise NotImplementedError
