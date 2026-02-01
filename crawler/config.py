"""
爬虫配置 - 会议代码映射和 DBLP URL 构建
"""

# 会议代码到 DBLP 路径的映射
DBLP_CONF_MAP = {
    'CCS': 'ccs',
    'SP': 'sp',
    'S&P': 'sp',
    'USS': 'uss',
    'NDSS': 'ndss',
    'ACSAC': 'acsac',
    'ESORICS': 'esorics',
    'DSN': 'dsn',
    'RAID': 'raid',
    'SRDS': 'srds',
    'CSFW': 'csfw',
    'SIGCOMM': 'sigcomm',
    'MOBICOM': 'mobicom',
    'INFOCOM': 'infocom',
    'NSDI': 'nsdi',
    'WWW': 'www',
}


def build_dblp_url(conference: str, year: int) -> str:
    """
    构建 DBLP URL

    Args:
        conference: 会议代码 (如 'CCS', 'SP', 'USS')
        year: 年份 (如 2024)

    Returns:
        str: DBLP 页面 URL

    Raises:
        ValueError: 当会议代码不支持时
    """
    conf = conference.upper()
    if conf not in DBLP_CONF_MAP:
        supported = ', '.join(sorted(DBLP_CONF_MAP.keys()))
        raise ValueError(
            f"Unknown conference: {conference}. "
            f"Supported conferences: {supported}"
        )
    code = DBLP_CONF_MAP[conf]
    return f"https://dblp.uni-trier.de/db/conf/{code}/{code}{year}.html"


def normalize_conference(conference: str) -> str:
    """
    标准化会议代码

    Args:
        conference: 会议代码

    Returns:
        str: 标准化后的会议代码（大写）
    """
    return conference.upper()
