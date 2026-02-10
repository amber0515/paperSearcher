#!/usr/bin/env python3
"""
基于 CCF 数据的 DBLP 论文爬虫 CLI

MVP 版本：支持按会议和年份爬取论文

使用示例:
    python -m crawler.dblp_cli CCS 2024
    python -m crawler.dblp_cli CCS,SP,USS 2024
    python -m crawler.dblp_cli --rank A --domain NIS 2024
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入 dblp 模块
from crawler.dblp import (
    build_year_url,
    fetch_papers,
    extract_papers_from_html,
    get_conferences_from_ccf,
    save_papers_to_db,
    Stats,
)

# 默认测试数据库路径
DEFAULT_TEST_DB = Path(__file__).parent.parent / "papers_test.db"


def main() -> int:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        description='基于 CCF 数据的 DBLP 论文爬虫',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
使用示例:
  python -m crawler.dblp_cli CCS 2024
  python -m crawler.dblp_cli CCS,SP,USS 2024
  python -m crawler.dblp_cli CCS 2022,2023,2024
  python -m crawler.dblp_cli --rank A --domain NIS 2024
  python -m crawler.dblp_cli CCS 2024 --preview-only --verbose  # 调试模式
        '''
    )

    parser.add_argument(
        'conferences',
        nargs='?',
        help='会议代码，多个用逗号分隔 (如 CCS,SP,USS)'
    )
    parser.add_argument(
        'years',
        help='年份，多个用逗号分隔 (如 2022,2023,2024)'
    )
    parser.add_argument(
        '--rank',
        choices=['A', 'B', 'C'],
        help='按 CCF 排名筛选 (A/B/C)'
    )
    parser.add_argument(
        '--domain',
        help='按领域筛选 (AI/NIS/CN/SE/DB/...)'
    )
    parser.add_argument(
        '--db',
        default=str(DEFAULT_TEST_DB),
        help=f'数据库路径 (默认: {DEFAULT_TEST_DB})'
    )
    parser.add_argument(
        '--preview-only',
        action='store_true',
        help='仅预览，不保存到数据库'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细信息（包括跳过的条目）'
    )

    args = parser.parse_args()

    # 检查依赖
    _check_dependencies()

    # 验证参数
    if not args.conferences and not args.rank:
        parser.error('请提供会议代码或使用 --rank/--domain 筛选')

    # 解析年份
    years = [int(y.strip()) for y in args.years.split(',')]

    print("=" * 60)
    print("基于 CCF 数据的 DBLP 论文爬虫")
    print(f"数据库: {args.db}")
    print("=" * 60)

    # 获取会议列表
    conferences = _get_conferences(args)

    if not conferences:
        print("错误: 未找到任何会议")
        return 1

    # 爬取论文
    total_stats = Stats()

    for venue in conferences:
        conf = venue['abbreviation']
        for year in years:
            print(f"\n[{conf} {year}]")

            # 构建 URL
            url = build_year_url(venue['dblp_url'], year)
            if not url:
                print(f"  错误: 无法构建 URL (dblp_url: {venue['dblp_url']})")
                continue

            print(f"  URL: {url}")

            try:
                # 获取页面
                html = fetch_papers(url)
                print(f"  获取到 {len(html):,} 字符")

                # 提取论文
                papers = extract_papers_from_html(html, conf, year, verbose=args.verbose)
                print(f"  找到 {len(papers)} 篇论文")

                if not papers:
                    continue

                # 预览模式：显示详细信息
                if args.preview_only:
                    _show_preview(papers)
                    continue

                # 非预览模式：仅显示前 3 篇
                _show_summary(papers)

                # 保存到数据库
                stats = save_papers_to_db(papers, args.db)
                print(f"  新增: {stats.added}, 跳过: {stats.skipped}, 错误: {stats.errors}")

                total_stats += stats

            except Exception as e:
                print(f"  错误: {e}")
                total_stats.errors += 1

    _print_summary(total_stats)
    return 0


def _check_dependencies() -> None:
    """检查必要的依赖"""
    try:
        from bs4 import BeautifulSoup
        from crawl4ai import AsyncWebCrawler
    except ImportError as e:
        print("错误: 缺少必要的依赖")
        print(f"  {e}")
        print("\n请安装依赖:")
        print("  pip install crawl4ai beautifulsoup4")
        sys.exit(1)


def _get_conferences(args) -> list:
    """获取会议列表"""
    if args.conferences:
        # 指定了具体会议
        conf_list = [c.strip().upper() for c in args.conferences.split(',')]
        conferences = []
        for conf in conf_list:
            venues = get_conferences_from_ccf(args.db, venue_type='conference')
            venue = next((v for v in venues if v['abbreviation'] == conf), None)
            if venue:
                conferences.append(venue)
            else:
                print(f"警告: 未找到会议 {conf}")
        return conferences
    else:
        # 使用筛选条件
        conferences = get_conferences_from_ccf(
            args.db,
            rank=args.rank,
            domain=args.domain,
            venue_type='conference'
        )
        print(f"找到 {len(conferences)} 个符合条件的会议")
        return conferences


def _show_preview(papers: list) -> None:
    """显示论文预览（详细模式）"""
    print(f"\n  📄 论文详情预览:")
    print(f"  {'─' * 70}")
    for i, p in enumerate(papers, 1):
        print(f"\n  [{i}] {p['title']}")
        print(f"      作者: {p['authors'] or '(未知)'}")
        print(f"      链接: {p['href']}")
        print(f"      年份: {p['year']}")
        print(f"      会议: {p['conference']}")
    print(f"\n  {'─' * 70}")
    print(f"  共 {len(papers)} 篇论文（预览模式，未保存）")


def _show_summary(papers: list) -> None:
    """显示简要摘要"""
    for i, p in enumerate(papers[:3], 1):
        print(f"    {i}. {p['title'][:60]}...")


def _print_summary(stats: Stats) -> None:
    """打印最终统计"""
    print("\n" + "=" * 60)
    print("完成!")
    print(f"总计 - 新增: {stats.added}, 跳过: {stats.skipped}, 错误: {stats.errors}")
    print("=" * 60)


if __name__ == '__main__':
    sys.exit(main())
