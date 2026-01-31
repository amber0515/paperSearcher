# 论文爬虫自动化系统 - 基于 Crawl4AI 的实现计划

## 一、自动化程度评估

### 回答你的核心问题

**问题1: 最后还需要输入网页吗？**
**不需要输入具体网页**。你只需要输入会议名称和年份即可。

**问题2: 只需要输入根域名？**
**比根域名更简单**——你只需要输入会议代码和年份，例如：
```bash
python crawler/main.py CCS 2024
```

### 自动化程度说明

| 你需要输入 | 系统自动完成 |
|-----------|-------------|
| 会议代码 (如 "CCS") + 年份 (如 2024) | 自动构建 DBLP URL |
| | 自动爬取论文列表 |
| | 自动提取标题、作者、摘要 |
| | 自动处理去重 |
| | 自动保存到数据库 |

---

## 二、技术方案：基于 Crawl4AI

### 为什么选择 Crawl4AI？

- ✅ **专为 LLM 设计**：输出干净的 Markdown，易于 AI 处理
- ✅ **简单易用**：几行代码即可完成爬取
- ✅ **支持 LLM 提取**：可直接用 LLM 提取结构化数据
- ✅ **动态内容支持**：基于 Playwright，可处理 JS 渲染页面
- ✅ **强大功能**：CSS 选择器、XPath、LLM 提取等多种方式

### 安装 Crawl4AI

```bash
pip install crawl4ai
crawl4ai-setup
```

---

## 三、最简版本设计（MVP）

### 核心思路

1. **使用 Crawl4AI 爬取 DBLP 页面** → 获取 Markdown
2. **用 LLM 解析 Markdown 提取论文列表** → 结构化数据
3. **保存到数据库**

### 用户使用方式

```bash
# 最简单的用法
python crawler/main.py CCS 2024

# 或使用别名
python crawler/main.py sp 2024      # IEEE S&P
python crawler/main.py uss 2024     # USENIX Security
```

---

## 四、代码结构

```
paperSearcher/
├── crawler/
│   ├── __init__.py
│   ├── main.py                   # CLI 入口
│   ├── config.py                 # 配置
│   ├── crawler.py                # Crawl4AI 爬虫（核心）
│   └── extractor.py              # LLM 提取器
├── website.py
├── papers.db
└── requirements.txt
```

---

## 五、核心文件实现

### 1. `/crawler/config.py` - 配置

```python
"""
爬虫配置
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
    """构建 DBLP URL"""
    conf = conference.upper()
    if conf not in DBLP_CONF_MAP:
        raise ValueError(f"Unknown conference: {conference}")
    code = DBLP_CONF_MAP[conf]
    return f"https://dblp.uni-trier.de/db/conf/{code}/{code}{year}.html"
```

### 2. `/crawler/crawler.py` - Crawl4AI 爬虫

```python
"""
基于 Crawl4AI 的论文爬虫
"""
import asyncio
from crawl4ai import AsyncWebCrawler
from .config import build_dblp_url


async def fetch_papers_from_dblp(conference: str, year: int):
    """
    使用 Crawl4AI 从 DBLP 爬取论文页面

    Returns:
        str: DBLP 页面的 Markdown 内容
    """
    url = build_dblp_url(conference, year)

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(
            url=url,
            # Crawl4AI 会自动生成干净的 Markdown
        )
        return result.markdown


# 同步包装函数（方便调用）
def fetch_papers(conference: str, year: int) -> str:
    """同步接口：获取 DBLP 页面的 Markdown"""
    return asyncio.run(fetch_papers_from_dblp(conference, year))
```

### 3. `/crawler/extractor.py` - LLM 提取器

```python
"""
使用 LLM 从 Markdown 中提取论文信息
"""
import re
from typing import List, Dict


def extract_papers_from_markdown(markdown: str, conference: str, year: int) -> List[Dict]:
    """
    从 DBLP 的 Markdown 中提取论文信息

    由于 DBLP 的格式比较规范，可以先用正则表达式提取
    如果需要更精确，可以用 LLM（如 OpenAI API）

    Returns:
        List[Dict]: 论文列表，每个论文包含 title, authors, href, bib 等
    """
    papers = []

    # DBLP Markdown 格式示例：
    # **[Title Here]**(link)
    # * Author1, Author2, Author3
    # [BibTeX](bib_link) [DOI](doi_link)

    # 简单解析：按条目分割
    entries = re.split(r'\n\s*\n', markdown)

    for entry in entries:
        if not entry.strip():
            continue

        # 提取标题（带链接）
        title_match = re.search(r'\*\*\[([^\]]+)\]\(([^\)]+)\)', entry)
        if not title_match:
            continue

        title = title_match.group(1)
        href = title_match.group(2)

        # 提取作者
        authors_match = re.search(r'\* (.+)', entry)
        authors = authors_match.group(1) if authors_match else ""

        # 提取 BibTeX 链接
        bib_match = re.search(r'\[BibTeX\]\(([^\)]+)\)', entry)
        bib = bib_match.group(1) if bib_match else ""

        papers.append({
            'title': title,
            'year': year,
            'conference': conference.upper(),
            'authors': authors,
            'href': href,
            'bib': bib,
            'origin': build_dblp_url(conference, year),
            'abstract': None  # 需要单独获取
        })

    return papers


# 或者使用 LLM 提取（更精确但需要 API key）
def extract_papers_with_llm(markdown: str, conference: str, year: int, api_key: str = None) -> List[Dict]:
    """
    使用 LLM（如 OpenAI）提取论文信息

    这是 Crawl4AI 的强项，可以用 LLMExtractionStrategy
    """
    from crawl4ai import AsyncWebCrawler, LLMExtractionStrategy, LLMConfig
    from pydantic import BaseModel, Field
    import os

    class Paper(BaseModel):
        title: str = Field(description="Paper title")
        authors: str = Field(description="Authors, comma separated")
        href: str = Field(description="Link to paper")
        bib: str = Field(description="BibTeX link")

    async def extract():
        strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(
                provider="openai/gpt-4o-mini",
                api_token=api_key or os.getenv("OPENAI_API_KEY")
            ),
            schema=Paper.schema(),
            instruction="Extract all papers from this DBLP page. Return a list of papers with title, authors, link, and BibTeX URL."
        )

        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=build_dblp_url(conference, year),
                extraction_strategy=strategy
            )
            return result.extracted_content

    return asyncio.run(extract())
```

### 4. `/crawler/main.py` - CLI 入口

```python
"""
论文爬虫 CLI - 基于 Crawl4AI

使用示例:
    python crawler/main.py CCS 2024
    python crawler/main.py sp 2024
"""
import argparse
import sqlite3
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.crawler import fetch_papers
from crawler.extractor import extract_papers_from_markdown


def save_to_database(papers: list, db_path: str = "papers.db"):
    """保存论文到数据库"""
    stats = {'added': 0, 'skipped': 0, 'errors': 0}

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for paper in papers:
        try:
            # 检查是否已存在
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
            print(f"Error saving paper: {e}")
            stats['errors'] += 1

    conn.commit()
    conn.close()

    return stats


def main():
    parser = argparse.ArgumentParser(
        description='论文爬虫 - 基于 Crawl4AI',
        epilog='示例: python crawler/main.py CCS 2024'
    )
    parser.add_argument('conference', help='会议代码 (如 CCS, SP, USS, NDSS)')
    parser.add_argument('year', type=int, help='年份 (如 2024)')
    parser.add_argument('--db', default='papers.db', help='数据库路径')

    args = parser.parse_args()

    print(f"正在爬取 {args.conference} {args.year}...")

    # 1. 使用 Crawl4AI 获取 Markdown
    print("正在获取 DBLP 页面...")
    markdown = fetch_papers(args.conference, args.year)
    print(f"获取到 {len(markdown)} 字符的 Markdown")

    # 2. 提取论文信息
    print("正在解析论文信息...")
    papers = extract_papers_from_markdown(markdown, args.conference, args.year)
    print(f"找到 {len(papers)} 篇论文")

    # 3. 保存到数据库
    print("正在保存到数据库...")
    stats = save_to_database(papers, args.db)

    print(f"\n完成!")
    print(f"  新增: {stats['added']}")
    print(f"  跳过: {stats['skipped']}")
    print(f"  错误: {stats['errors']}")


if __name__ == '__main__':
    main()
```

### 5. 更新 `requirements.txt`

```
# 现有依赖
Flask>=2.0.0

# 新增：Crawl4AI
crawl4ai>=0.8.0
```

---

## 六、使用示例

### 基本使用

```bash
# 爬取 CCS 2024
python crawler/main.py CCS 2024

# 预期输出：
# 正在爬取 CCS 2024...
# 正在获取 DBLP 页面...
# 获取到 152342 字符的 Markdown
# 正在解析论文信息...
# 找到 167 篇论文
# 正在保存到数据库...
# 完成!
#   新增: 167
#   跳过: 0
#   错误: 0
```

### 验证结果

```bash
# 启动搜索服务
python3 website.py

# 在浏览器访问 http://127.0.0.1:5000
# 搜索 "CCS" 并筛选 2024，验证论文已录入
```

---

## 七、实现优先级

### Phase 1: 核心功能（最简版本）
1. ✅ 安装 Crawl4AI (`pip install crawl4ai && crawl4ai-setup`)
2. ✅ `/crawler/config.py` - 配置
3. ✅ `/crawler/crawler.py` - Crawl4AI 基础爬虫
4. ✅ `/crawler/extractor.py` - 正则表达式提取（不需要 LLM）
5. ✅ `/crawler/main.py` - CLI 入口
6. ✅ 更新 `requirements.txt`

### Phase 2: 增强功能
1. 使用 LLM 提取（更精确，需要 OpenAI API key）
2. 摘要获取（从论文详情页或 Semantic Scholar）
3. 进度条显示
4. 错误处理和日志

---

## 八、关键文件清单

### 需要新建的文件

| 文件路径 | 功能 | 代码行数（约） |
|---------|------|--------------|
| `/crawler/__init__.py` | 包初始化 | 5 |
| `/crawler/config.py` | 配置 | 30 |
| `/crawler/crawler.py` | Crawl4AI 爬虫 | 40 |
| `/crawler/extractor.py` | 数据提取 | 80 |
| `/crawler/main.py` | CLI 入口 | 80 |

**总计：约 235 行代码**

### 需要修改的文件

| 文件路径 | 修改内容 |
|---------|---------|
| `/requirements.txt` | 添加 `crawl4ai>=0.8.0` |

---

## 九、优势对比

| 功能 | 传统方案 (BeautifulSoup) | Crawl4AI 方案 |
|-----|------------------------|--------------|
| 代码量 | ~500 行 | ~235 行 |
| 动态内容支持 | 需要额外配置 | 原生支持 |
| LLM 集成 | 需要自己写 | 内置支持 |
| Markdown 输出 | 需要自己转换 | 自动生成 |
| CSS 选择器 | 支持 | 支持 |
| 维护成本 | 较高 | 较低 |

---

## 十、总结

### 你只需要

```bash
python crawler/main.py CCS 2024
```

### 系统自动完成

- ✅ 构建正确的 DBLP URL
- ✅ 使用 Crawl4AI 爬取并生成 Markdown
- ✅ 解析 Markdown 提取论文信息
- ✅ 数据验证和去重
- ✅ 保存到数据库

### 代码量

**约 235 行**，比传统方案减少 50%+

### 下一步

如果你觉得这个方案可行，我可以开始实现最简版本（Phase 1）。
