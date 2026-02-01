"""
CCF Metadata Crawler CLI
抓取 CCF 推荐会议和期刊目录

使用示例:
    python -m crawler.ccf.cli --preview-only
    python -m crawler.ccf.cli
    python -m crawler.ccf.cli --db papers_test.db
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from crawler.ccf.crawler import fetch_all_ccf_pages, CCF_DOMAIN_CODES
from crawler.ccf.parser import parse_all_ccf_pages
from crawler.ccf.database import save_ccf_venues, get_statistics


def print_venues_preview(venues: list):
    """
    按领域打印 A 类会议/期刊预览

    Args:
        venues: venue 列表
    """
    # 领域名称映射
    DOMAIN_NAMES = {
        'ARCH': '计算机体系结构/并行与分布计算/存储系统',
        'CN': '计算机网络',
        'NIS': '网络与信息安全',
        'SE': '软件工程/系统软件/程序设计语言',
        'DB': '数据库/数据挖掘/内容检索',
        'TC': '计算机科学理论',
        'GM': '计算机图形学与多媒体',
        'AI': '人工智能',
        'HCI': '人机交互与普适计算',
        'Cross': '交叉/综合/新兴',
    }

    # 按领域和类型分组，只取 A 类
    from collections import defaultdict
    grouped = defaultdict(lambda: {'journal': [], 'conference': []})

    for v in venues:
        if v['ccf_rank'] == 'A':
            if v['venue_type'] == 'journal':
                grouped[v['domain']]['journal'].append(v)
            else:
                grouped[v['domain']]['conference'].append(v)

    print(f"\n{'=' * 80}")
    print("CCF A 类刊物和会议")
    print(f"{'=' * 80}")

    for domain in sorted(grouped.keys()):
        data = grouped[domain]

        print(f"\n【{domain}】{DOMAIN_NAMES.get(domain, domain)}")
        print("-" * 60)

        if data['journal']:
            print(f"\n  A 类刊物 ({len(data['journal'])}):")
            for v in data['journal']:
                dblp = v.get('dblp_url', '')
                if dblp:
                    print(f"    {v['abbreviation']} - {v['publisher']} - {dblp}")
                else:
                    print(f"    {v['abbreviation']} - {v['publisher']}")

        if data['conference']:
            print(f"\n  A 类会议 ({len(data['conference'])}):")
            for v in data['conference']:
                dblp = v.get('dblp_url', '')
                if dblp:
                    print(f"    {v['abbreviation']} - {v['publisher']} - {dblp}")
                else:
                    print(f"    {v['abbreviation']} - {v['publisher']}")

        if not data['journal'] and not data['conference']:
            print("  (无 A 类数据)")

    print(f"\n{'=' * 80}")


def main():
    parser = argparse.ArgumentParser(
        description='CCF 会议/期刊元数据爬虫',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  python -m crawler.ccf.cli --preview-only
  python -m crawler.ccf.cli
  python -m crawler.ccf.cli --db papers_test.db
        '''
    )
    parser.add_argument(
        '--db',
        default=None,
        help='数据库路径 (默认: papers_test.db)'
    )
    parser.add_argument(
        '--preview-only',
        action='store_true',
        help='仅预览，不保存到数据库'
    )
    parser.add_argument(
        '--domains',
        nargs='*',
        choices=list(CCF_DOMAIN_CODES.keys()),
        help='指定抓取的领域 (默认: 全部)'
    )

    args = parser.parse_args()

    # 默认使用测试数据库
    db_path = args.db if args.db else str(Path(project_root) / "papers_test.db")

    print("=" * 80)
    print("CCF 会议/期刊元数据爬虫")
    print(f"数据库: {db_path}")
    if args.domains:
        print(f"领域: {', '.join(args.domains)}")
    else:
        print(f"领域: 全部 ({len(CCF_DOMAIN_CODES)} 个)")
    print("=" * 80)

    try:
        # 1. 抓取所有领域页面
        print("\n[1/3] 正在抓取 CCF 官网数据...")
        html_dict = fetch_all_ccf_pages()
        total_html = sum(1 for h in html_dict.values() if h)
        print(f"      成功抓取 {total_html}/{len(CCF_DOMAIN_CODES)} 个领域")

        # 2. 解析数据
        print("\n[2/3] 正在解析数据...")
        venues = parse_all_ccf_pages(html_dict)
        print(f"      共解析出 {len(venues)} 个会议/期刊")

        if len(venues) == 0:
            print("\n警告: 未解析到任何数据。请检查网络连接和页面格式。")
            return 1

        # 3. 显示预览
        print_venues_preview(venues)

        # 4. 保存到数据库
        if args.preview_only:
            print("\n预览模式 - 数据未保存到数据库")
            return 0

        print(f"\n[3/3] 正在保存到数据库...")
        stats = save_ccf_venues(venues, db_path)

        # 5. 显示结果
        print(f"\n完成!")
        print(f"  新增: {stats['added']}")
        print(f"  更新: {stats['updated']}")
        print(f"  错误: {stats['errors']}")

        # 6. 显示统计
        db_stats = get_statistics(db_path)
        print(f"\n数据库统计:")
        print(f"  总数: {db_stats['total']}")
        print(f"  按等级: {db_stats['by_rank']}")
        print(f"  按类型: {db_stats['by_type']}")

        return 0

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
