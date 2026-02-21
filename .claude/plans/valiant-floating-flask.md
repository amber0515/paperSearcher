# 论文摘要获取模块重构计划

## 背景

用户希望将摘要获取功能从 `crawler/dblp/` 分离到独立的 `crawler/abstract/` 文件夹，保持 dblp 文件夹不变。

## 重构方案

### 目录结构

```
crawler/
├── dblp/                    # 保持不变：论文列表爬虫
│   ├── __init__.py
│   ├── models.py
│   ├── url_builder.py
│   ├── fetcher.py
│   ├── parser.py
│   ├── database.py
│   └── cli.py               # 命令: python -m crawler.dblp.cli CCS 2024
│
└── abstract/                # 新增：论文摘要获取
    ├── __init__.py
    ├── doi_extractor.py     # 从 dblp/ 复制
    ├── api_clients.py      # 从 dblp/ 复制
    ├── abstract_fetcher.py # 从 dblp/ 复制
    └── cli.py              # 从 dblp/batch_cli.py 改造
```

### CLI 命令

**论文列表爬取（不变）：**
```bash
python -m crawler.dblp.cli CCS 2024
python -m crawler.dblp.cli CCS,SP,USS 2024
```

**摘要获取（新命令）：**
```bash
python -m crawler.abstract.cli --db papers.db --conf CCS --year 2024
python -m crawler.abstract.cli --db papers.db --limit 1000
python -m crawler.abstract.cli --db papers.db --refresh
```

### 实现步骤

1. **创建 `crawler/abstract/` 目录**
2. **复制文件**：
   - 复制 `doi_extractor.py`
   - 复制 `api_clients.py`
   - 复制 `abstract_fetcher.py`
   - 复制并改造 `batch_cli.py` 为 `cli.py`
3. **创建 `crawler/abstract/__init__.py`**
4. **保留 `crawler/dblp/batch_cli.py`** 作为兼容层（可选）

（验证由用户自行完成）
