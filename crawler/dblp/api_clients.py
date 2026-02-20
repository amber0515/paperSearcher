"""
API 客户端模块

提供 Crossref 和 Semantic Scholar API 客户端。
"""
import time
import logging
import requests
from typing import Optional
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)


class CrossrefClient:
    """Crossref API 客户端"""

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, email: str = "research@example.com"):
        """
        初始化客户端

        Args:
            email: 用于 API 请求的邮箱（Crossref 建议提供）
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'PaperSearcher/1.0 (mailto:{email})'
        })

    def get_abstract(self, doi: str) -> Optional[str]:
        """
        获取论文摘要

        Args:
            doi: DOI 字符串

        Returns:
            摘要文本或 None
        """
        try:
            url = f"{self.BASE_URL}/{doi}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            item = data.get('message', {})

            # 尝试从 abstract 字段获取
            abstract = item.get('abstract')

            if abstract:
                return self._clean_abstract(abstract)

            # 尝试从 subtitle 组合
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

    def _clean_abstract(self, abstract: str) -> str:
        """
        清理 JATS XML 格式的摘要

        Crossref 的 abstract 通常是 JATS XML 格式
        """
        if not abstract:
            return ""

        # 移除 XML 标签
        try:
            # 尝试解析为 XML
            root = ET.fromstring(f"<root>{abstract}</root>")
            # 获取所有文本
            texts = []
            for elem in root.iter():
                if elem.text:
                    texts.append(elem.text)
                if elem.tail:
                    texts.append(elem.tail)
            result = ' '.join(texts)
        except ET.ParseError:
            # 如果不是有效 XML，直接移除标签
            result = abstract

        # 清理多余空白
        result = ' '.join(result.split())

        return result


class SemanticScholarClient:
    """Semantic Scholar API 客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"

    # 免费版限制: 100 次/5分钟
    RATE_LIMIT = 100
    RATE_WINDOW = 300  # 5 分钟

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json'
        })
        self._request_times = []

    def get_abstract(self, doi: str) -> Optional[str]:
        """
        获取论文摘要

        Args:
            doi: DOI 字符串

        Returns:
            摘要文本或 None
        """
        self._wait_for_rate_limit()

        try:
            # 使用 DOI:{doi} 格式
            paper_id = f"DOI:{doi}"
            url = f"{self.BASE_URL}/{paper_id}"
            params = {
                'fields': 'abstract'
            }

            response = self.session.get(url, params=params, timeout=10)
            self._request_times.append(time.time())

            if response.status_code == 404:
                return None

            response.raise_for_status()

            data = response.json()
            abstract = data.get('abstract')

            if abstract:
                return ' '.join(abstract.split())

            return None

        except requests.RequestException as e:
            logger.debug(f"Semantic Scholar API error for {doi}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"Semantic Scholar parse error for {doi}: {e}")
            return None

    def get_abstract_arxiv(self, arxiv_id: str) -> Optional[str]:
        """
        从 Semantic Scholar 获取 arXiv 论文摘要

        Args:
            arxiv_id: arXiv ID (如 1706.03762)

        Returns:
            摘要文本或 None
        """
        self._wait_for_rate_limit()

        try:
            # 使用 arXiv:{id} 格式
            paper_id = f"arXiv:{arxiv_id}"
            url = f"{self.BASE_URL}/{paper_id}"
            params = {
                'fields': 'abstract'
            }

            response = self.session.get(url, params=params, timeout=10)
            self._request_times.append(time.time())

            if response.status_code == 404:
                return None

            if response.status_code == 429:
                # Rate limited
                logger.debug("Semantic Scholar rate limited")
                return None

            response.raise_for_status()

            data = response.json()
            abstract = data.get('abstract')

            if abstract:
                return ' '.join(abstract.split())

            return None

        except requests.RequestException as e:
            logger.debug(f"Semantic Scholar API error for arXiv {arxiv_id}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"Semantic Scholar parse error for arXiv {arxiv_id}: {e}")
            return None

    def _wait_for_rate_limit(self):
        """等待直到可以进行下一个请求"""
        now = time.time()

        # 清理过期的请求记录
        self._request_times = [
            t for t in self._request_times
            if now - t < self.RATE_WINDOW
        ]

        # 如果已达到限制，等待
        if len(self._request_times) >= self.RATE_LIMIT:
            oldest = self._request_times[0]
            wait_time = self.RATE_WINDOW - (now - oldest)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)


# 默认客户端实例
_crossref_client: Optional[CrossrefClient] = None
_semantic_scholar_client: Optional[SemanticScholarClient] = None


def get_crossref_client() -> CrossrefClient:
    """获取 Crossref 客户端单例"""
    global _crossref_client
    if _crossref_client is None:
        _crossref_client = CrossrefClient()
    return _crossref_client


def get_semantic_scholar_client() -> SemanticScholarClient:
    """获取 Semantic Scholar 客户端单例"""
    global _semantic_scholar_client
    if _semantic_scholar_client is None:
        _semantic_scholar_client = SemanticScholarClient()
    return _semantic_scholar_client
