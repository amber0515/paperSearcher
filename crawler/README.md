# 爬虫模块

论文数据采集系统，包含三个爬虫模块和一个共享模块。

## 模块结构

```
crawler/
├── shared/              # 共享模块
│   ├── database.py      # 统一数据库操作
│   └── models.py        # 通用数据模型
│
├── dblp/                # DBLP 论文爬虫
│   ├── cli.py           # CLI 入口
│   ├── fetcher.py       # 网页获取
│   ├── parser.py        # HTML 解析
│   └── url_builder.py   # URL 构建
│
├── ccf/                 # CCF 排名爬虫
│   ├── cli.py           # CLI 入口
│   ├── fetcher.py       # 网页获取
│   └── parser.py        # HTML 解析
│
└── abstract/            # 论文摘要获取
    ├── cli.py           # CLI 入口
    ├── fetcher.py       # 摘要获取调度
    ├── doi_extractor.py # DOI 提取
    ├── api_providers/   # API 提供者
    │   ├── crossref.py
    │   ├── openalex.py
    │   └── semantic_scholar.py
    └── origin_extractors/ # 原始网站提取器
        ├── base.py
        ├── usenix.py
        ├── ndss.py
        └── llm.py
```

## 采集策略

### 论文数据 (dblp)

1. 从 CCF 数据库获取会议/期刊列表
2. 构建 DBLP URL
3. 爬取论文列表页面
4. 解析论文信息（标题、作者、链接等）

### CCF 排名 (ccf)

1. 爬取 CCF 官网各领域排名页面
2. 解析会议/期刊信息
3. 存储到 ccf_venues 表

### 论文摘要 (abstract)

#### 获取优先级

```
1. 有专属提取器 → 直接使用专属提取器
2. 无专属提取器 → API (Semantic Scholar → OpenAlex)
3. 都失败 → LLM 提取器 (兜底)
```

#### 详细流程

```
① 有专属提取器? (usenix.org, ndss-symposium.org 等)
   │
   ├─ 是 → 专属提取器提取
   │    ├─ 成功 → 返回
   │    └─ 失败 → 步骤 ②
   │
   └─ 否 → 步骤 ②

② API 提取
   │
   ├─ Semantic Scholar (DOI)
   │    ├─ 成功 → 返回
   │    └─ 失败 → OpenAlex (DOI)
   │
   ├─ OpenAlex (DOI)
   │    ├─ 成功 → 返回
   │    └─ 失败 → OpenAlex (标题)
   │
   ├─ OpenAlex (标题)
   │    ├─ 成功 → 返回
   │    └─ 失败 → Semantic Scholar (标题)
   │
   └─ Semantic Scholar (标题)
        ├─ 成功 → 返回
        └─ 失败 → 步骤 ③

③ LLM 提取器 (兜底)
   ├─ 成功 → 返回
   └─ 失败 → 返回 None
```

## 运行

```bash
# DBLP 论文爬虫
* 网安顶会顶刊
python -m crawler.dblp.cli CCS,USS,SP,NDSS,CRYPTO,EUROCRYPT,TIFS,TDSCS 2024
* 测试
python -m crawler.dblp.cli USS 2025 --preview-only --verbose

# CCF 排名爬虫
python -m crawler.ccf.cli --preview-only

# 摘要获取
python -m crawler.abstract.cli --db papers_test.db
```

## 设计原则

1. **各模块职责分离**：只负责爬取/解析，不关心数据库
2. **统一数据库操作**：shared/database.py 管理所有表操作
3. **可扩展的提取器**：按需添加新的网站提取器或 API 提供者
4. **摘要获取兜底**：专用提取器失败后使用 LLM
