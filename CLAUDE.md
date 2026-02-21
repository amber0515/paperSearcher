# CLAUDE.md

基于 Flask 的学术论文搜索 Web 应用，支持多领域学术论文检索和自动化爬虫。

## 项目结构

```
paperSearcher/
├── website.py              # Flask 后端
├── config.py               # 环境配置
├── requirements.txt        # 依赖
│
├── crawler/
│   ├── dblp/              # DBLP 论文爬虫
│   │   ├── cli.py         # CLI 入口
│   │   ├── url_builder.py # URL 构建
│   │   ├── fetcher.py     # 网页获取
│   │   ├── parser.py      # HTML 解析
│   │   ├── database.py    # 数据库操作
│   │   └── models.py      # 数据模型
│   │
│   ├── abstract/          # 论文摘要获取
│   │   ├── cli.py         # CLI 入口
│   │   ├── fetcher.py    # 摘要获取器
│   │   ├── api_clients.py # API 客户端
│   │   ├── doi_extractor.py # DOI 提取
│   │   └── database.py   # 复用共享数据库函数
│   │
│   ├── shared/            # 共享模块
│   │   └── database.py   # 通用数据库操作
│   │
│   └── ccf/              # CCF 排名爬虫
│
├── papers.db              # 生产数据库
└── papers_test.db         # 测试数据库
```

## 运行

```bash
# Web 服务器
python website.py                    # 测试环境
ENV=prod python website.py          # 生产环境

# DBLP 爬虫
python -m crawler.dblp.cli CCS 2024           # 爬取会议论文
python -m crawler.dblp.cli USS 2025 --preview-only --verbose

# 摘要获取
python -m crawler.abstract.cli --db papers.db --limit 1000
python -m crawler.abstract.cli --db papers.db --refresh

# CCF 爬虫
python -m crawler.ccf.cli --preview-only
```

## 数据库

**papers 表**：
- `id`, `conference`, `year`, `title`, `href`, `origin`, `abstract`, `bib`, `cat`

- `href`: DBLP 详情页链接
- `origin`: 原始会议/期刊网站链接（如 usenix.org, dl.acm.org）

## 搜索 API

- `GET /search?q=关键词` - 搜索论文
- `GET /abstract/<id>` - 获取摘要
