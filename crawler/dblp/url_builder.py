"""
URL 构建模块

提供从 DBLP 基础 URL 构建年份特定 URL 的功能。
"""

# ============================================================
# 特殊会议 URL 配置区
# ============================================================
#
# 配置格式：
#   1. 范围模式（有规律多场次）: {"template": "模板", "range": [起始, 结束]}
#   2. 完整URL列表: ["url1", "url2", ...]
#   3. 单一模板: ["{base}xxx{year}.html"]
#
# 模板变量: {base}=基础URL, {year}=年份, {code}=会议代码, {n}=场次编号
#
# 示例:
SPECIAL_URLS = {
    "CRYPTO": {
        "2025": {"template": "{base}/crypto{year}-{n}.html", "range": [1, 8]},  # crypto2025-1.html ~ crypto2025-8.html
    },
    "EUROCRYPT": {
        "2025": {"template": "{base}/eurocrypt{year}-{n}.html", "range": [1, 8]},
    },
    # "SP": ["{base}sp{year}.html"],  # 简单模板
}
# ============================================================


def build_year_url(dblp_url: str, conf_abbr: str, year: int) -> str | None:
    """构建年份特定 URL（返回主URL）"""
    urls = build_year_url_all(dblp_url, conf_abbr, year)
    return urls[0] if urls else None


def build_year_url_all(dblp_url: str, conf_abbr: str, year: int) -> list[str]:
    """
    构建所有可能的年份特定 URL（支持多场次）

    模板变量: {base}, {year}, {code}, {n}
    """
    if not dblp_url:
        return []

    base = dblp_url.rstrip('/')
    # 从 dblp_url 中提取会议代码（最后一个路径部分）
    # 例如：http://dblp.uni-trier.de/db/conf/uss/ -> uss
    code = base.split('/')[-1]
    urls = []

    # 检查是否有特殊 URL 配置
    if conf_abbr in SPECIAL_URLS:
        config = SPECIAL_URLS[conf_abbr]

        if isinstance(config, dict):
            # 字典格式：按年份/年份范围配置
            patterns = _get_patterns_for_year(config, year)
        elif isinstance(config, list):
            # 数组格式：所有年份统一
            patterns = config
        elif isinstance(config, str):
            # 字符串格式：单个模板
            patterns = [config]
        else:
            patterns = None

        if patterns:
            # 检查是否是范围模式
            if isinstance(patterns, dict) and 'template' in patterns and 'range' in patterns:
                # 范围模式：生成多个URL
                template = patterns['template']
                start, end = patterns['range']
                for n in range(start, end + 1):
                    url = template.format(base=base, year=year, code=code, n=n)
                    urls.append(url)
            else:
                # 标准模式：列表或单个值
                for pattern in patterns:
                    # 判断是完整URL还是模板
                    if isinstance(pattern, str) and pattern.startswith('http'):
                        # 完整URL，直接使用
                        urls.append(pattern)
                    else:
                        # 模板字符串，进行替换
                        urls.append(pattern.format(base=base, year=year, code=code))
            if urls:
                return urls

    # 默认标准格式
    return [f"{base}/{code}{year}.html"]


def _get_patterns_for_year(config: dict, year: int) -> list[str] | None:
    """
    从配置中获取指定年份的URL模式

    年份语法: "2025", "2025+", "2020-2024", "default"
    """
    year_str = str(year)

    # 1. 检查精确匹配的年份
    if year_str in config:
        return config[year_str]

    # 2. 检查年份范围
    for key, patterns in config.items():
        if key == "default":
            continue

        if '+' in key:
            # "2025+": 2025年及以后
            base_year = int(key.rstrip('+'))
            if year >= base_year:
                return patterns
        elif '-' in key:
            # "2020-2024" 或 "2020-" 或 "-2020"
            if key.startswith('-'):
                # "-2020": 2020年及以前
                end_year = int(key.lstrip('-'))
                if year <= end_year:
                    return patterns
            elif key.endswith('-'):
                # "2020-": 2020年及以后
                start_year = int(key.rstrip('-'))
                if year >= start_year:
                    return patterns
            else:
                # "2020-2024": 范围
                parts = key.split('-')
                if len(parts) == 2:
                    start_year = int(parts[0])
                    end_year = int(parts[1])
                    if start_year <= year <= end_year:
                        return patterns

    # 3. 使用默认模式
    return config.get("default")
