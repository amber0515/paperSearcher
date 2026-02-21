"""Crossref API 提供者"""
import logging
import requests
from typing import Optional
from xml.etree import ElementTree as ET
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class CrossrefClient(BaseAPIClient):
    """Crossref API 客户端"""

    BASE_URL = "https://api.crossref.org/works"

    @property
    def name(self) -> str:
        return "crossref"

    def __init__(self, email: str = "research@example.com"):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'PaperSearcher/1.0 (mailto:{email})'
        })

    def get_abstract(self, doi: str) -> Optional[str]:
        try:
            url = f"{self.BASE_URL}/{doi}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            item = data.get('message', {})

            abstract = item.get('abstract')
            if abstract:
                return self._clean_abstract(abstract)

            subtitle = item.get('subtitle', [])
            if subtitle:
                return ' '.join(subtitle)

            return None

        except requests.RequestException as e:
            logger.debug(f"Crossref API error for {doi}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"Crossref parse error for {doi}: {e}")
            return None

    def search_by_title(self, title: str) -> Optional[str]:
        """Crossref 不支持标题搜索，返回 None"""
        return None

    def get_abstract_arxiv(self, arxiv_id: str) -> Optional[str]:
        """Crossref 不支持 arXiv ID，返回 None"""
        return None

    def _clean_abstract(self, abstract: str) -> str:
        """清理 JATS XML 格式的摘要"""
        if not abstract:
            return ""

        try:
            root = ET.fromstring(f"<root>{abstract}</root>")
            texts = []
            for elem in root.iter():
                if elem.text:
                    texts.append(elem.text)
                if elem.tail:
                    texts.append(elem.tail)
            result = ' '.join(texts)
        except ET.ParseError:
            result = abstract

        result = ' '.join(result.split())
        return result
