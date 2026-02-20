"""
批量获取论文摘要 CLI

用法:
    python -m crawler.dblp.batch_cli --db papers.db --limit 1000
    python -m crawler.dblp.batch_cli --db papers.db --refresh
    python -m crawler.dblp.batch_cli --db papers.db --conf CCS --year 2024
"""
import argparse
import asyncio
import logging
import sys
import time

from crawler.dblp.database import (
    get_papers_without_abstract,
    get_papers_for_refresh,
    update_paper_abstract,
)
from crawler.dblp.abstract_fetcher import AbstractFetcher


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fetch_abstracts(
    db_path: str,
    limit: int = 100,
    conference: str = None,
    year: int = None,
    delay: float = 0.5,
    verbose: bool = False,
    refresh: bool = False
):
    """
    批量获取论文摘要

    Args:
        db_path: 数据库路径
        limit: 获取数量
        conference: 会议筛选
        year: 年份筛选
        delay: 请求间隔（秒）
        verbose: 详细输出
        refresh: 刷新已有摘要
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 获取需要处理论文
    if refresh:
        papers = get_papers_for_refresh(
            db_path,
            limit=limit,
            conference=conference,
            year=year,
            has_doi=True
        )
    else:
        papers = get_papers_without_abstract(
            db_path,
            limit=limit,
            conference=conference,
            year=year
        )

    if not papers:
        logger.info("没有需要处理的论文")
        return

    logger.info(f"找到 {len(papers)} 篇需要获取摘要的论文")

    fetcher = AbstractFetcher()
    success = 0
    failed = 0
    skipped = 0

    try:
        for i, paper in enumerate(papers, 1):
            paper_id = paper['id']
            title = paper['title']
            href = paper.get('href', '')
            origin = paper.get('origin', '')

            if verbose:
                logger.info(f"[{i}/{len(papers)}] 处理: {title[:50]}...")

            try:
                abstract, source = await fetcher.fetch_abstract(
                    title=title,
                    href=href,
                    origin=origin
                )

                if abstract:
                    # 更新数据库
                    if update_paper_abstract(db_path, paper_id, abstract, source):
                        success += 1
                        logger.info(f"  ✓ 成功 (来源: {source})")
                    else:
                        failed += 1
                        logger.warning(f"  ✗ 更新失败")
                else:
                    skipped += 1
                    logger.debug(f"  - 跳过 (无摘要)")

            except Exception as e:
                failed += 1
                logger.error(f"  ✗ 错误: {e}")

            # 请求间隔
            if delay > 0 and i < len(papers):
                time.sleep(delay)

    finally:
        await fetcher.close()

    # 统计结果
    logger.info("=" * 50)
    logger.info(f"完成! 成功: {success}, 跳过: {skipped}, 失败: {failed}")
    logger.info(f"成功率: {success*100/(success+failed+skipped):.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="批量获取论文摘要",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python -m crawler.dblp.batch_cli --db papers.db --limit 100
    python -m crawler.dblp.batch_cli --db papers.db --conf CCS --year 2024
    python -m crawler.dblp.batch_cli --db papers.db --refresh --limit 5000
        """
    )

    parser.add_argument(
        '--db',
        default='papers.db',
        help='数据库路径 (默认: papers.db)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='处理论文数量限制 (默认: 100)'
    )

    parser.add_argument(
        '--conf',
        help='会议缩写筛选 (如 CCS, USS, OSDI)'
    )

    parser.add_argument(
        '--year',
        type=int,
        help='年份筛选'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='请求间隔秒数 (默认: 0.5)'
    )

    parser.add_argument(
        '--refresh',
        action='store_true',
        help='刷新已有摘要 (重新获取)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出'
    )

    args = parser.parse_args()

    # 检查数据库文件
    import os
    if not os.path.exists(args.db):
        logger.error(f"数据库文件不存在: {args.db}")
        sys.exit(1)

    # 运行
    try:
        asyncio.run(fetch_abstracts(
            db_path=args.db,
            limit=args.limit,
            conference=args.conf,
            year=args.year,
            delay=args.delay,
            verbose=args.verbose,
            refresh=args.refresh
        ))
    except KeyboardInterrupt:
        logger.info("用户中断")
        sys.exit(1)


if __name__ == '__main__':
    main()
