# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 概述

这是一个基于 Flask 的学术论文搜索 Web 应用，支持多领域学术论文检索和自动化爬虫功能。系统包含：

- **Web 搜索界面**：本地搜索服务，连接包含 76,000+ 篇论文的 SQLite 数据库
- **自动化爬虫**：从 DBLP 爬取论文数据，从 CCF 爬取会议/期刊排名信息
- **双环境支持**：测试环境和生产环境分离

覆盖领域包括：网络安全、计算机网络、人工智能、软件工程、数据库等，涵盖 CCS、S&P、USENIX Security、NDSS、ICML、NeurIPS、AAAI 等顶级会议。

## 项目结构

```
paperSearcher/
├── website.py              # Flask 后端服务器
├── config.py               # 环境配置管理
├── requirements.txt        # Python 依赖
├── .env.example           # 环境变量模板
│
├── crawler/               # 论文爬虫模块
│   ├── main.py           # CLI 入口
│   ├── crawler.py        # Crawl4AI 爬虫
│   ├── extractor.py      # HTML/Markdown 解析
│   └── config.py         # 会议映射配置
│
├── crawler/ccf/           # CCF 排名爬虫模块
│   ├── cli.py            # CLI 入口
│   ├── crawler.py        # CCF 网站爬虫
│   ├── parser.py         # CCF 数据解析
│   └── database.py       # CCF 数据库操作
│
├── plans/                # 开发计划和文档
├── docs/                 # 项目文档
├── static/               # 前端资源
│
├── papers.db             # 生产数据库 (154 MB, 76,442 篇论文)
└── papers.db.zip         # 压缩备份
```

## 运行应用

### 首次设置

```bash
# 解压数据库
unzip paper.db.zip

# 安装依赖
pip3 install -r requirements.txt

# 安装 Crawl4AI（爬虫功能需要）
pip install crawl4ai
crawl4ai-setup
```

### 启动 Web 服务器

```bash
# 测试环境（默认）
python3 website.py
# 使用 papers_test.db

# 生产环境
ENV=prod python3 website.py
# 使用 papers.db，需要确认启动

# 自定义 host/port
python3 website.py 0.0.0.0 8080
```

### 使用爬虫

```bash
# 爬取 DBLP 论文（按会议和年份）
python crawler/main.py CCS 2024
python crawler/main.py sp 2023 --db papers_test.db

# 爬取 CCF 排名信息（仅预览）
python -m crawler.ccf.cli --preview-only

# 保存 CCF 数据到数据库
python -m crawler.ccf.cli --db papers_test.db
```

## 核心功能

### Web 搜索 API

**[website.py](website.py)** 提供两个主要 endpoints：

- `GET /search` - 关键词搜索，支持分页、会议和年份筛选
- `GET /abstract/<paper_id>` - 获取论文摘要

**搜索语法**（支持布尔逻辑）：
- `+` 表示 AND（两个关键词都必须匹配）
- `|` 表示 OR（任一关键词匹配即可）

示例：
- `blockchain+security` → 同时包含 "blockchain" AND "security"
- `security|iot` → 包含 "security" OR "iot"

### 环境管理

**[config.py](config.py)** 提供：
- 测试/生产环境切换
- 数据库自动初始化
- 输入验证规则
- 生产环境启动安全确认

支持的会议（28 个）：CCS, SP, USS, NDSS, SIGCOMM, ICML, NIPS, AAAI, ICLR, KDD, WWW, SenSys, INFOCOM, 等

### 爬虫模块

**[crawler/](crawler/)** - DBLP 论文爬虫：
- 支持 23 个会议的论文爬取
- 提取标题、作者、链接、BibTeX
- 基于 Crawl4AI 的高效爬取

**[crawler/ccf/](crawler/ccf/)** - CCF 排名爬虫：
- 爬取 CCF 官方会议/期刊排名
- 覆盖 10 个领域（AI、网络与安全、软件工程等）
- 存储 A/B/C 级分类信息

## 数据库

### PAPER 表结构

| 字段 | 说明 |
|------|------|
| `id` | 主键 |
| `conf` | 会议/期刊名称 |
| `year` | 年份 |
| `cat` | 类别 |
| `title` | 论文标题 |
| `href` | 论文链接 |
| `abstract` | 摘要 |
| `bib` | BibTeX 引文 |

### 统计信息

- **总论文数**：76,442 篇
- **数据库大小**：154 MB
- **年份范围**：2016-2025
- **顶级会议论文数**：
  - NIPS: 16,526 篇
  - AAAI: 15,159 篇
  - ICML: 8,711 篇

## 安全特性

代码已从早期版本改进，现在使用：
- **参数化查询**：防止 SQL 注入（使用 `?` 占位符）
- **输入验证**：关键词长度限制、会议白名单、年份范围检查
- **环境隔离**：测试和生产数据库分离
- **本地运行建议**：建议仅在本地（`127.0.0.1`）运行

## 配置文件

### .env.example

```bash
ENV=test  # 或 'prod' 切换生产环境
```

### 配置常量 (config.py)

- `ALLOWED_CONFERENCES`: 28 个支持的会议
- `MIN_YEAR`, `MAX_YEAR`: 2016-2025
- `MAX_KEYWORD_LENGTH`: 200 字符
- `MAX_LIMIT`: 每页最多 100 篇论文

## 开发计划

详见 [plans/](plans/) 目录：
- [CRAWLER_PLAN.md](plans/CRAWLER_PLAN.md) - 论文爬虫实现计划
- [CCF_INTEGRATION_PLAN.md](plans/CCF_INTEGRATION_PLAN.md) - CCF 集成计划
- [CONFIG_PLAN.md](plans/CONFIG_PLAN.md) - 配置管理计划
- [DB_GUI_PLAN.md](plans/DB_GUI_PLAN.md) - 数据库 GUI 工具指南

## 依赖项

主要依赖：
- `Flask==2.0.1` - Web 框架
- `werkzeug<3.0.0` - WSGI 工具集
- `crawl4ai>=0.4.0` - Web 爬虫（新增）
- `beautifulsoup4>=4.9.0` - HTML 解析（新增）
