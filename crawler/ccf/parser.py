"""
Parse CCF ranking data from official website Markdown
"""
import re
from typing import List, Dict


def parse_ccf_html(markdown: str, domain_code: str) -> List[Dict]:
    """
    解析 CCF 官网 Markdown 内容，提取期刊和会议信息

    格式示例:
        #### 中国计算机学会推荐国际学术刊物
        #### (● 计算机网络)
        ### A类
          * 序号
        刊物名称
        刊物全称
        出版社
        地址
          * 1
        JSAC
        IEEE Journal...
        IEEE

    Args:
        markdown: CCF 官网 Markdown 内容
        domain_code: 领域代码 (如 'CN', 'NIS', 'AI')

    Returns:
        List[Dict]: 解析后的 venue 列表
    """
    venues = []
    lines = markdown.split('\n')

    i = 0
    current_section = None  # 'journal' or 'conference'
    current_rank = None     # 'A', 'B', 'C'

    # 常见出版社名称（用于检测）
    COMMON_PUBLISHERS = {
        'ACM', 'IEEE', 'Springer', 'Elsevier', 'USENIX', 'MIT Press',
        'ACM/IEEE', 'IEEE/ACM', 'ISOC', 'AAAI', 'SIAM', 'APSCE'
    }

    # 编译正则表达式
    journal_pattern = re.compile(r'中国计算机学会推荐国际学术刊物', re.IGNORECASE)
    conference_pattern = re.compile(r'中国计算机学会推荐国际学术会议', re.IGNORECASE)
    rank_pattern = re.compile(r'^###\s*([ABC])类')

    while i < len(lines):
        line = lines[i].strip()

        # 检测期刊部分
        if journal_pattern.search(line):
            current_section = 'journal'
            i += 1
            continue

        # 检测会议部分
        if conference_pattern.search(line):
            current_section = 'conference'
            i += 1
            continue

        # 检测 A/B/C 类 (### A类)
        rank_match = rank_pattern.search(line)
        if rank_match:
            current_rank = rank_match.group(1)
            i += 1
            continue

        # 检测条目（以 * 和数字开头，如 "  * 1"）
        if line.startswith('*') and line[1:].strip().isdigit() and current_section and current_rank:
            # 下一个非空行是缩写
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                abbreviation = lines[j].strip()
                # 下一个是全称
                k = j + 1
                while k < len(lines) and not lines[k].strip():
                    k += 1

                full_name = ''
                publisher = ''
                dblp_url = None

                if k < len(lines):
                    line_k = lines[k].strip()
                    # 检查这一行是否是 dblp 链接 (说明没有单独的全称行)
                    if line_k.startswith('<http') and line_k.endswith('>'):
                        # 缩写即是全称，这一行是 dblp 链接
                        full_name = abbreviation
                        dblp_url = line_k[1:-1]
                        # 检查下一行是否有出版社
                        l = k + 1
                        while l < len(lines) and not lines[l].strip():
                            l += 1
                        if l < len(lines):
                            line_l = lines[l].strip()
                            # 如果不是下一组条目，也不是链接，则是出版社
                            if not (line_l.startswith('*') and line_l[1:].strip().isdigit()) and \
                               not (line_l.startswith('<http') and line_l.endswith('>')):
                                publisher = line_l
                    elif line_k in COMMON_PUBLISHERS:
                        # 这一行是出版社，说明缩写即是全称
                        full_name = abbreviation
                        publisher = line_k
                        # 检查下一行是否是 dblp 链接
                        l = k + 1
                        while l < len(lines) and not lines[l].strip():
                            l += 1
                        if l < len(lines):
                            line_l = lines[l].strip()
                            if line_l.startswith('<http') and line_l.endswith('>'):
                                dblp_url = line_l[1:-1]
                    else:
                        # 正常情况：这一行是全称
                        full_name = line_k
                        # 下一个是出版社
                        l = k + 1
                        while l < len(lines) and not lines[l].strip():
                            l += 1
                        if l < len(lines):
                            line_l = lines[l].strip()
                            # 检查是否是 dblp 链接
                            if line_l.startswith('<http') and line_l.endswith('>'):
                                # 出版社为空，这一行是 dblp 链接
                                dblp_url = line_l[1:-1]
                            else:
                                # 正常情况：这一行是出版社
                                publisher = line_l
                                # 检查下一行是否是 dblp 链接
                                m = l + 1
                                while m < len(lines) and not lines[m].strip():
                                    m += 1
                                if m < len(lines):
                                    line_m = lines[m].strip()
                                    if line_m.startswith('<http') and line_m.endswith('>'):
                                        dblp_url = line_m[1:-1]

                if abbreviation and full_name:
                    venues.append({
                        'abbreviation': abbreviation,
                        'full_name': full_name,
                        'publisher': publisher,
                        'ccf_rank': current_rank,
                        'venue_type': current_section,
                        'domain': domain_code,
                        'dblp_url': dblp_url
                    })

        i += 1

    return venues


def parse_all_ccf_pages(markdown_dict: Dict[str, str]) -> List[Dict]:
    """
    解析所有领域的 CCF 页面

    Args:
        markdown_dict: {domain_code: markdown_content}

    Returns:
        List[Dict]: 所有解析后的 venue 列表
    """
    all_venues = []

    for domain_code, markdown in markdown_dict.items():
        if markdown:
            try:
                venues = parse_ccf_html(markdown, domain_code)
                all_venues.extend(venues)
                print(f"  Parsed {len(venues)} venues from {domain_code}")
            except Exception as e:
                print(f"  Error parsing {domain_code}: {e}")

    return all_venues
