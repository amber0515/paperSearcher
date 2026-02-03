# CCF 会议/期刊收录计划

## 目标
将 CCF 认定的全部会议和期刊收录到数据库中，作为后续论文管理的索引依据。

---

## 数据库设计

### 新建表：`ccf_venues`

```sql
CREATE TABLE ccf_venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    abbreviation TEXT NOT NULL UNIQUE,        -- 缩写，如 'CCS', 'SIGCOMM', 'TIFS'
    full_name TEXT NOT NULL,                  -- 完整英文名称
    publisher TEXT,                           -- ACM, IEEE, USENIX 等
    ccf_rank TEXT NOT NULL,                   -- 'A', 'B', 或 'C'
    venue_type TEXT NOT NULL,                 -- 'conference' 或 'journal'
    domain TEXT NOT NULL,                     -- 专业领域代码 (10 个领域)
    dblp_url TEXT,                            -- DBLP 链接
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_ccf_abbreviation ON ccf_venues(abbreviation);
CREATE INDEX idx_ccf_rank ON ccf_venues(ccf_rank);
CREATE INDEX idx_ccf_type ON ccf_venues(venue_type);
CREATE INDEX idx_ccf_domain ON ccf_venues(domain);
```

### 专业领域映射

| 代码                  | 领域                                   |
| --------------------- | -------------------------------------- |
| ARCH                  | 计算机体系结构/并行与分布计算/存储系统 |
| CN                    | 计算机网络                             |
| NIS                   | 网络与信息安全                         |
| SE                    | 软件工程/系统软件/程序设计语言         |
| DB                    | 数据库/数据挖掘/内容检索               |
| TC                    | 计算机科学理论                         |
| GM                    | 计算机图形学与多媒体                   |
| AI                    | 人工智能                               |
| HCIAndPC              | 人机交互与普适计算                     |
| Cross_Compre_Emerging | 交叉/综合/新兴                         |

---

## 目录结构

```
crawler/
├── ccf/                     # CCF 爬虫模块（独立目录）
│   ├── __init__.py
│   ├── crawler.py           # 使用 Crawl4AI 抓取 CCF 网站
│   ├── parser.py            # 解析 HTML/Markdown 数据
│   ├── database.py          # 数据库操作 (保存/查询)
│   └── cli.py               # 命令行接口
├── __init__.py
├── main.py                  # 现有爬虫
├── crawler.py               # 现有爬虫 (使用 Crawl4AI)
├── extractor.py             # 现有解析器
└── config.py                # 现有配置
```

---

## 爬虫实现

### 数据源
- **主数据源**: https://ccf.atom.im/ (单页面，结构化数据，易于解析)
- **备用数据源**: https://www.ccf.org.cn/Academic_Evaluation/By_category/

### 使用 Crawl4AI 抓取

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def fetch_ccf_page() -> str:
    """
    使用 Crawl4AI 获取 CCF 网站内容
    """
    url = "https://ccf.atom.im/"

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            # 使用 markdown 格式解析更简单
            return result.markdown
        else:
            raise Exception(f"Failed to fetch: {result.error_message}")
```

### CLI 使用方式

```bash
# 预览数据（不保存）
python -m crawler.ccf.cli --preview-only

# 抓取到测试数据库（默认）
python -m crawler.ccf.cli

# 指定数据库
python -m crawler.ccf.cli --db papers_test.db
```

**注意**: 默认使用 `papers_test.db` 测试环境，不会影响生产数据。

---

## 最小版本 (MVP)

### Phase 0: 最小可用版本

**目标**: 快速验证方案可行性

#### 文件结构
```
crawler/ccf/
├── __init__.py
├── crawler.py       # 使用 Crawl4AI 抓取网页
├── parser.py        # 解析 Markdown 数据（含 dblp_url）
├── database.py      # 存储到 papers_test.db
└── cli.py           # 简单 CLI
```

#### 功能范围
- [x] 使用 **Crawl4AI** 从 https://ccf.atom.im/ 抓取全部数据
- [x] 解析：abbreviation, full_name, publisher, ccf_rank, venue_type, domain, dblp_url
- [x] 创建 `ccf_venues` 表（测试数据库）
- [x] 保存数据到 `papers_test.db`
- [x] CLI 预览和保存功能

#### 验证方式
```bash
# 1. 运行爬虫
python -m crawler.ccf.cli --preview-only --preview 5

# 2. 保存到测试数据库
python -m crawler.ccf.cli

# 3. 验证数据
sqlite3 papers_test.db
> SELECT * FROM ccf_venues LIMIT 5;
> SELECT domain, COUNT(*) FROM ccf_venues GROUP BY domain;
```

---

## 完整版本（后续扩展）

### 新增接口

| 接口                   | 功能                                                |
| ---------------------- | --------------------------------------------------- |
| `GET /api/ccf/venues`  | 获取 CCF 会议/期刊列表 (支持 rank/type/domain 筛选) |
| `GET /api/ccf/domains` | 获取各领域统计信息                                  |

### 修改的文件

| 文件         | 修改内容                             |
| ------------ | ------------------------------------ |
| `config.py`  | 添加 CCF_DOMAINS, CCF_RANKS 等配置   |
| `website.py` | 添加 CCF API 接口，支持 CCF 等级筛选 |

---

## 实现步骤

### Phase 0: 最小版本 (当前)
- [ ] 创建 `crawler/ccf/` 目录结构
- [ ] 实现 `crawler.py` - **使用 Crawl4AI 抓取网页**
- [ ] 实现 `parser.py` - 解析 Markdown 数据（含 dblp_url）
- [ ] 实现 `database.py` - 存储到测试数据库
- [ ] 实现 `cli.py` - CLI 工具
- [ ] 验证数据正确性

### Phase 1: 后端集成 (MVP 后)
- [ ] 更新 `config.py` 添加 CCF 配置
- [ ] 实现基础 API 接口
- [ ] 测试 API

### Phase 2: 搜索集成
- [ ] 修改搜索接口支持 CCF 筛选
- [ ] 前端展示 CCF 等级

---

## 验证方法

### SQL 验证
```sql
-- 打开测试数据库
sqlite3 papers_test.db

-- 检查表结构
.schema ccf_venues

-- 检查各领域会议数量
SELECT domain, COUNT(*) FROM ccf_venues GROUP BY domain;

-- 检查等级分布
SELECT ccf_rank, venue_type, COUNT(*) FROM ccf_venues GROUP BY ccf_rank, venue_type;

-- 验证已知会议
SELECT * FROM ccf_venues WHERE abbreviation IN ('CCS', 'SIGCOMM', 'NeurIPS');

-- 检查 dblp_url 是否正确
SELECT abbreviation, dblp_url FROM ccf_venues WHERE dblp_url IS NOT NULL LIMIT 5;
```

---

## 关键文件清单

### 新建文件 (MVP)
- `crawler/ccf/__init__.py`
- `crawler/ccf/crawler.py` - **使用 Crawl4AI**
- `crawler/ccf/parser.py`
- `crawler/ccf/database.py`
- `crawler/ccf/cli.py`

### 后续修改
- `config.py` (Phase 1)
- `website.py` (Phase 1)

---

## 参考现有代码

参考 `crawler/crawler.py` 中使用 Crawl4AI 的方式：

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def fetch_papers_from_dblp(conference: str, year: int) -> str:
    url = build_dblp_url(conference, year)

    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url)
        if result.success:
            return result.html  # 或 result.markdown
        else:
            raise Exception(f"Failed: {result.error_message}")

def fetch_papers(conference: str, year: int) -> str:
    return asyncio.run(fetch_papers_from_dblp(conference, year))
```
