"""Semantic Scholar API 提供者"""
import time
import logging
import requests
from typing import Optional
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class SemanticScholarClient(BaseAPIClient):
    """Semantic Scholar API 客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper"

    RATE_LIMIT = 1
    RATE_WINDOW = 1.5

    @property
    def name(self) -> str:
        return "semantic_scholar"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json'
        })
        self._request_times = []

    def get_abstract(self, doi: str) -> Optional[str]:
        self._wait_for_rate_limit()

        try:
            paper_id = f"DOI:{doi}"
            url = f"{self.BASE_URL}/{paper_id}"
            params = {'fields': 'abstract'}

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
        self._wait_for_rate_limit()

        try:
            paper_id = f"arXiv:{arxiv_id}"
            url = f"{self.BASE_URL}/{paper_id}"
            params = {'fields': 'abstract'}

            response = self.session.get(url, params=params, timeout=10)
            self._request_times.append(time.time())

            if response.status_code == 404:
                return None

            if response.status_code == 429:
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

    def search_by_title(self, title: str) -> Optional[str]:
        time.sleep(2)

        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'query': title,
                'fields': 'abstract,title',
                'limit': 1
            }

            response = self.session.get(url, params=params, timeout=15)

            if response.status_code == 404:
                return None

            if response.status_code == 429:
                logger.warning("Semantic Scholar 搜索被限流")
                return None

            response.raise_for_status()

            data = response.json()
            papers = data.get('data', [])

            if not papers:
                return None

            paper = papers[0]
            abstract = paper.get('abstract')

            if abstract:
                return ' '.join(abstract.split())

            return None

        except requests.RequestException as e:
            logger.warning(f"Semantic Scholar 网络错误: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"Semantic Scholar search parse error: {e}")
            return None

    def _wait_for_rate_limit(self):
        now = time.time()
        self._request_times = [
            t for t in self._request_times
            if now - t < self.RATE_WINDOW
        ]

        if len(self._request_times) >= self.RATE_LIMIT:
            oldest = self._request_times[0]
            wait_time = self.RATE_WINDOW - (now - oldest)
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
