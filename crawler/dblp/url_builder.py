"""
URL 构建模块

提供从 DBLP 基础 URL 构建年份特定 URL 的功能。
"""

# ============================================================
# 特殊会议 URL 配置区
# ============================================================
#
# 配置格式：
#   1. 直接URL: "年份": "完整URL"（期刊推荐）
#   2. 范围模式: {"template": "...", "range": [起始, 结束]}（多场次）
#   3. URL列表: ["url1", "url2"]（备用）
#
# 模板变量: {base}=基础URL, {year}=年份, {code}=会议代码, {n}=场次编号
#
# 示例:
SPECIAL_URLS = {
    # 会议：多场次
    "CRYPTO": {"template": "{base}/crypto{year}-{n}.html", "range": [1, 8]},  # crypto2025-1.html ~ crypto2025-8.html
    "EUROCRYPT": {"template": "{base}/eurocrypt{year}-{n}.html", "range": [1, 8]},

    # 期刊：年份→卷次映射
    "TIFS": {"volume_offset": -2004},  # 2025年 = 第21卷 (tifs21.html)
    "TDSC": {"volume_offset": -2003},  # 2025年 = 第22卷 (tdsc23.html)

    # 特殊会议代码映射（用于从完整名称提取 DBLP URL 代码）
    # 数据库中 abbreviation 可能是 "USENIX Security"，但 DBLP URL 需要 "uss"
    "USENIX SECURITY": "uss",
    "USENIX Security": "uss",
    "S&P": "sp",
}
# ============================================================


def build_year_url(dblp_url: str, conf_abbr: str, year: int) -> str | None:
    """构建年份特定 URL（返回主URL）"""
    return build_year_url_all(dblp_url, conf_abbr, year)[0] if build_year_url_all(dblp_url, conf_abbr, year) else None


def build_year_url_all(dblp_url: str, conf_abbr: str, year: int) -> list[str]:
    """构建所有可能的年份特定 URL（支持多场次）

    模板变量: {base}, {year}, {code}, {n}, {volume}
    """
    if not dblp_url:
        return []

    base = dblp_url.rstrip('/')

    # 优先使用特殊代码映射，否则使用 abbreviation 的小写
    if conf_abbr in SPECIAL_URLS and isinstance(SPECIAL_URLS[conf_abbr], str):
        code = SPECIAL_URLS[conf_abbr]
    else:
        code = conf_abbr.lower()

    urls = []

    # 检查特殊 URL 配置
    if conf_abbr in SPECIAL_URLS:
        config = SPECIAL_URLS[conf_abbr]

        # 期刊卷号模式
        if isinstance(config, dict) and 'volume_offset' in config:
            volume = year + config['volume_offset']
            return [f"{base}/{code}{volume}.html"]

        # 通用模式处理
        if isinstance(config, dict) and 'template' in config and 'range' in config:
            template = config['template']
            start, end = config['range']
            return [template.format(base=base, year=year, code=code, n=n) for n in range(start, end + 1)]

        if isinstance(config, list):
            urls = config
        elif isinstance(config, str):
            # 字符串可能是代码映射（如 "uss"）或直接 URL
            # 只有包含 "http" 或 ".html" 才视为直接 URL
            if 'http' in config or config.startswith('/') or config.endswith('.html'):
                urls = [config]
            # 否则这只是代码映射，不设置 urls，使用默认格式

    # 默认标准格式
    if not urls:
        return [f"{base}/{code}{year}.html"]

    return urls
