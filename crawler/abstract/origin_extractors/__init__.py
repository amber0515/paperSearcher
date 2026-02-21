"""原始网站提取器模块

按域名分发的专用提取器，按需加载，没有则用 LLM。
"""
from typing import Optional, Type

from .base import BaseExtractor
from .usenix import UsenixExtractor
from .ndss import NDSSExtractor
from .llm import LLMExtractor, get_llm_extractor, close_llm_extractor


# 提取器映射表（按域名）
EXTRACTORS: dict[str, Type[BaseExtractor]] = {
    "usenix.org": UsenixExtractor,
    "usenixsecurity.org": UsenixExtractor,
    "ndss-symposium.org": NDSSExtractor,
    # 未来添加:
    # "acm.org": AcmExtractor,
    # "ieee.org": IeeeExtractor,
    # "springer.com": SpringerExtractor,
}


def get_extractor(origin_url: str) -> Optional[BaseExtractor]:
    """根据 URL 返回对应的提取器

    Args:
        origin_url: 原始网站 URL

    Returns:
        对应的提取器实例，没有匹配返回 None
    """
    if not origin_url:
        return None

    for domain, extractor_cls in EXTRACTORS.items():
        if domain in origin_url.lower():
            return extractor_cls()
    return None


__all__ = [
    "BaseExtractor",
    "UsenixExtractor",
    "NDSSExtractor",
    "LLMExtractor",
    "get_extractor",
    "get_llm_extractor",
    "close_llm_extractor",
]
