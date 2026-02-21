"""NDSS 提取器"""
import re
from typing import Optional
from .base import BaseExtractor


class NDSSExtractor(BaseExtractor):
    """NDSS 提取器

    支持从 ndss-symposium.org 提取论文摘要。
    """

    def extract(self, html: str) -> Optional[str]:
        """从 NDSS HTML 页面中提取摘要

        NDSS 论文详情页结构:
        - P0: empty
        - P1: authors - "Name (Institution), Name (Institution), ..."
        - P2-P3: empty
        - P4+: abstract - 实际的论文摘要
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'html.parser')

        # 在 article 标签中查找摘要
        article = soup.select_one('article')
        if not article:
            return None

        # 查找所有段落
        paragraphs = article.find_all('p')

        for p in paragraphs:
            text = p.get_text(strip=True)

            # 跳过太短的文本
            if len(text) < 100:
                continue

            # 跳过作者行：包含多个 "名字 (机构)" 模式
            # 作者行特征：至少2个括号对，且至少1个逗号
            paren_count = text.count('(')
            comma_count = text.count(',')
            if paren_count >= 2 and comma_count >= 1:
                # 进一步验证：确认是作者格式（每个括号对前面有名字）
                if re.search(r'[A-Z][a-z]+ [A-Z][a-z]+ \([^)]+\)', text):
                    continue

            # 找到摘要了
            return self._clean(text)

        return None

    def _clean(self, text: str) -> str:
        """清理文本"""
        # 移除多余空白
        text = ' '.join(text.split())
        return text.strip()
