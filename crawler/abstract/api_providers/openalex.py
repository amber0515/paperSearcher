"""OpenAlex API 提供者"""
import time
import logging
import requests
from typing import Optional
from .base import BaseAPIClient

logger = logging.getLogger(__name__)


class OpenAlexClient(BaseAPIClient):
    """OpenAlex API 客户端

    优势:
    - 免费，无需 API Key
    - 每秒 10 次请求
    - 覆盖 2 亿+ 学术论文
    """

    BASE_URL = "https://api.openalex.org/works"

    RATE_LIMIT = 10
    RATE_WINDOW = 1.0

    @property
    def name(self) -> str:
        return "openalex"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PaperSearcher/1.0 (https://github.com/yourname/paperSearcher)'
        })
        self._request_times = []

    def get_abstract(self, doi: str) -> Optional[str]:
        self._wait_for_rate_limit()

        try:
            url = self.BASE_URL
            params = {
                'filter': f'doi:{doi}',
                'per-page': 1
            }

            response = self.session.get(url, params=params, timeout=10)
            self._request_times.append(time.time())

            if response.status_code == 404:
                return None

            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                return None

            abstract = results[0].get('abstract_inverted_index')
            if abstract:
                return self._reconstruct_abstract(abstract)

            return None

        except requests.RequestException as e:
            logger.debug(f"OpenAlex API error for {doi}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"OpenAlex parse error for {doi}: {e}")
            return None

    def search_by_title(self, title: str) -> Optional[str]:
        """通过标题搜索获取摘要"""
        self._wait_for_rate_limit()

        try:
            url = self.BASE_URL
            params = {
                'search': title,
                'per-page': 5
            }

            response = self.session.get(url, params=params, timeout=15)
            self._request_times.append(time.time())

            if response.status_code == 404:
                return None

            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            if not results:
                return None

            # 尝试找到最佳匹配
            for paper in results:
                paper_title = paper.get('title', '').lower()
                title_lower = title.lower()

                title_words = set(title_lower.split())
                paper_words = set(paper_title.split())

                if title_words and paper_words:
                    overlap = len(title_words & paper_words) / len(title_words)
                    if overlap >= 0.6:
                        abstract = paper.get('abstract_inverted_index')
                        if abstract:
                            return self._reconstruct_abstract(abstract)

            return None

        except requests.RequestException as e:
            logger.debug(f"OpenAlex search error for '{title}': {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"OpenAlex search parse error: {e}")
            return None

    def get_abstract_arxiv(self, arxiv_id: str) -> Optional[str]:
        """暂不支持 arXiv"""
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
                time.sleep(wait_time)

    def _reconstruct_abstract(self, abstract_inverted_index: dict) -> str:
        if not abstract_inverted_index:
            return ""

        position_to_word = {}
        for word, positions in abstract_inverted_index.items():
            for pos in positions:
                position_to_word[pos] = word

        if not position_to_word:
            return ""

        max_pos = max(position_to_word.keys())
        words = []
        for pos in range(0, max_pos + 1):
            if pos in position_to_word:
                words.append(position_to_word[pos])

        return ' '.join(words)
