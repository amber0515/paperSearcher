#!/usr/bin/env python3
"""
论文爬虫 CLI - 基于 Crawl4AI

使用示例:
    python -m crawler.main CCS 2024
    python crawler/main.py sp 2024
    python crawler/main.py USS 2023 --db papers_test.db
"""
import argparse
import sqlite3
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crawler.crawler import fetch_papers
from crawler.extractor import extract_papers_from_markdown
import config


def save_to_database(papers: list, db_path: str) -> dict:
    """
    保存论文到数据库

    Args:
        papers: 论文列表
        db_path: 数据库路径

    Returns:
        dict: 统计信息 {'added': int, 'skipped': int, 'errors': int}
    """
    stats = {'added': 0, 'skipped': 0, 'errors': 0}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for paper in papers:
        try:
            # 检查是否已存在（通过标题唯一性）
            cursor.execute(
                "SELECT id FROM papers WHERE title = ?",
                (paper['title'],)
            )
            if cursor.fetchone():
                stats['skipped'] += 1
                continue

            # 插入新论文
            cursor.execute("""
                INSERT INTO papers
                (conference, year, title, href, origin, bib)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                paper['conference'],
                paper['year'],
                paper['title'],
                paper.get('href', ''),
                paper.get('origin', ''),
                paper.get('bib', '')
            ))
            stats['added'] += 1

        except Exception as e:
            print(f"Error saving paper '{paper.get('title', 'Unknown')}': {e}")
            stats['errors'] += 1

    conn.commit()
    conn.close()

    return stats


def print_papers_preview(papers: list, limit: int = 5):
    """
    打印论文预览（前几篇）

    Args:
        papers: 论文列表
        limit: 显示数量
    """
    print(f"\n论文预览 (前 {min(limit, len(papers))} 篇):")
    print("-" * 60)
    for i, paper in enumerate(papers[:limit], 1):
        print(f"{i}. {paper['title']}")
        print(f"   作者: {paper.get('authors', 'N/A')}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='论文爬虫 - 基于 Crawl4AI',
        epilog='示例: python -m crawler.main CCS 2024',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'conference',
        help='会议代码 (如 CCS, SP, USS, NDSS, SIGCOMM)'
    )
    parser.add_argument(
        'year',
        type=int,
        help='年份 (如 2024)'
    )
    parser.add_argument(
        '--db',
        default=None,
        help=f'数据库路径 (默认: {config.DB_PATH})'
    )
    parser.add_argument(
        '--preview',
        type=int,
        default=5,
        metavar='N',
        help='显示预览论文数量 (默认: 5)'
    )
    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='不显示论文预览'
    )

    args = parser.parse_args()

    # 使用当前环境的数据库路径（如果未指定）
    db_path = args.db if args.db else config.DB_PATH

    print(f"=" * 60)
    print(f"论文爬虫 - {args.conference.upper()} {args.year}")
    print(f"数据库: {db_path}")
    print(f"环境: {config.ENV_NAME}")
    print(f"=" * 60)

    try:
        # 1. 使用 Crawl4AI 获取 Markdown
        print("\n[1/3] 正在获取 DBLP 页面...")
        markdown = fetch_papers(args.conference, args.year)
        print(f"      获取到 {len(markdown):,} 字符的 Markdown")

        # 2. 提取论文信息
        print("\n[2/3] 正在解析论文信息...")
        papers = extract_papers_from_markdown(
            markdown, args.conference, args.year
        )
        print(f"      找到 {len(papers)} 篇论文")

        if len(papers) == 0:
            print("\n警告: 未找到任何论文。请检查:")
            print("  1. 会议代码和年份是否正确")
            print("  2. 网络连接是否正常")
            print("  3. DBLP 是否有该年份的数据")
            return 1

        # 3. 显示预览
        if not args.no_preview:
            print_papers_preview(papers, args.preview)

        # 4. 保存到数据库
        print(f"\n[3/3] 正在保存到数据库...")
        stats = save_to_database(papers, db_path)

        # 5. 显示结果
        print(f"\n完成!")
        print(f"  新增: {stats['added']}")
        print(f"  跳过: {stats['skipped']} (已存在)")
        print(f"  错误: {stats['errors']}")

        if stats['added'] == 0 and stats['skipped'] > 0:
            print("\n提示: 所有论文已存在于数据库中")
        elif stats['added'] > 0:
            print(f"\n提示: 启动搜索服务查看结果: python3 website.py")

        return 0

    except ValueError as e:
        print(f"\n错误: {e}")
        return 1
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
