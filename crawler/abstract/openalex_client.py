"""
OpenAlex API 客户端

提供通过 DOI 或标题搜索获取论文摘要的功能。
"""
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class OpenAlexClient:
    """OpenAlex API 客户端

    优势:
    - 免费，无需 API Key
    - 每秒 10 次请求（比 Semantic Scholar 宽松 10 倍）
    - 覆盖 2 亿+ 学术论文
    """

    BASE_URL = "https://api.openalex.org/works"

    # 限制: 10 次/秒
    RATE_LIMIT = 10
    RATE_WINDOW = 1.0  # 1 秒

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PaperSearcher/1.0 (https://github.com/yourname/paperSearcher)'
        })
        self._request_times = []

    def get_abstract(self, doi: str) -> Optional[str]:
        """
        通过 DOI 获取论文摘要

        Args:
            doi: DOI 字符串 (如 10.1145/3580305.3599234)

        Returns:
            摘要文本或 None
        """
        self._wait_for_rate_limit()

        try:
            # OpenAlex 使用 DOI 作为过滤条件
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
                # OpenAlex 的 abstract 是倒排索引格式，需要重建
                return self._reconstruct_abstract(abstract)

            return None

        except requests.RequestException as e:
            logger.debug(f"OpenAlex API error for {doi}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.debug(f"OpenAlex parse error for {doi}: {e}")
            return None

    def search_by_title(self, title: str) -> Optional[str]:
        """
        通过标题搜索论文并获取摘要

        Args:
            title: 论文标题

        Returns:
            摘要文本或 None
        """
        self._wait_for_rate_limit()

        try:
            # 使用搜索 API
            url = self.BASE_URL
            params = {
                'search': title,
                'per-page': 5  # 获取前 5 个结果以便更好地匹配
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

                # 检查标题是否足够相似（简单匹配：包含主要单词）
                title_words = set(title_lower.split())
                paper_words = set(paper_title.split())

                # 如果匹配度超过 60%，则认为匹配成功
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
                time.sleep(wait_time)

    def _reconstruct_abstract(self, abstract_inverted_index: dict) -> str:
        """
        从倒排索引重建摘要文本

        OpenAlex 的 abstract 是倒排索引格式:
        {
            "word1": [position1, position2, ...],
            "word2": [position1, ...],
            ...
        }
        """
        if not abstract_inverted_index:
            return ""

        # 构建位置到词的映射
        position_to_word = {}
        for word, positions in abstract_inverted_index.items():
            # positions 是一个整数列表，如 [0, 18]
            for pos in positions:
                position_to_word[pos] = word

        # 按位置顺序重建文本
        if not position_to_word:
            return ""

        max_pos = max(position_to_word.keys())
        words = []
        for pos in range(0, max_pos + 1):
            if pos in position_to_word:
                words.append(position_to_word[pos])

        return ' '.join(words)


# 默认客户端实例
_openalex_client: Optional[OpenAlexClient] = None


def get_openalex_client() -> OpenAlexClient:
    """获取 OpenAlex 客户端单例"""
    global _openalex_client
    if _openalex_client is None:
        _openalex_client = OpenAlexClient()
    return _openalex_client
