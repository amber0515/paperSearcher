"""USENIX 提取器"""
import re
from typing import Optional
from .base import BaseExtractor


class UsenixExtractor(BaseExtractor):
    """USENIX 提取器

    支持 usenix.org 和 usenixsecurity.org
    """

    def extract(self, html: str) -> Optional[str]:
        # 尝试多种 USENIX 摘要模式
        patterns = [
            # USENIX standard: <div class="field field-name-field-paper-description">
            r'<div[^>]*class=["\'][^"\']*field-paper-description[^"\']*["\'][^>]*>.*?<p[^>]*>(.*?)</p>',

            # Alternative pattern with field-name
            r'<div[^>]*class=["\'][^"\']*field-paper-description[^"\']*["\'][^>]*>(.*?)</div>',

            # USENIX Security specific
            r'<div[^>]*class=["\'][^"\']*field-paper-abstract[^"\']*["\'][^>]*>.*?<p[^>]*>(.*?)</p>',

            # Generic description field
            r'<div[^>]*class=["\'][^"\']*field-name-field-paper-description[^"\']*["\'][^>]*>(.*?)</div>',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                abstract = self._clean(match.group(1))
                if abstract and len(abstract) > 20:
                    return abstract

        return None

    def _clean(self, text: str) -> str:
        """清理 HTML 标签和实体"""
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除多余空白
        text = ' '.join(text.split())
        # 替换 HTML 实体
        entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
        }
        for entity, char in entities.items():
            text = text.replace(entity, char)
        return text.strip()
