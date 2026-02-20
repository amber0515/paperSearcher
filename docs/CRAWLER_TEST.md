# DBLP 爬虫测试指南

## 1. 初始化测试数据库

```bash
# 创建测试数据库表结构
python -c "from config import init_test_db; init_test_db()"
```

## 2. 爬取论文数据

### 基本爬取

```bash
# 爬取 CCS 2024 论文
python -m crawler.dblp.cli CCS 2024 --db papers_test.db

# 爬取 USENIX Security 2024 论文
python -m crawler.dblp.cli USS 2024 --db papers_test.db

# 爬取 S&P 2024 论文
python -m crawler.dblp.cli SP 2024 --db papers_test.db
```

### 预览模式

```bash
# 只预览不保存 - 网安顶会 & 顶刊 - 论文列表
python -m crawler.dblp.cli CCS,USS,SP,CRYPTO,EUROCRYPT,TIFS,TDSC 2024 --preview-only
```

### 查看数据

```bash
# 查看爬取的论文数量
sqlite3 papers_test.db "SELECT COUNT(*) FROM papers"

# 查看论文详情
sqlite3 papers_test.db "SELECT id, title, href, origin FROM papers LIMIT 5"
```

## 3. 获取论文摘要

### 批量获取摘要

```bash
# 为没有摘要的论文获取摘要（默认100篇）
python -m crawler.dblp.batch_cli --db papers_test.db --verbose

# 指定数量
python -m crawler.dblp.batch_cli --db papers_test.db --limit 500 --verbose

# 刷新已有摘要（使用 DOI 筛选）
python -m crawler.dblp.batch_cli --db papers_test.db --refresh --limit 100 --verbose
```

### 按会议/年份筛选

```bash
# 只处理 CCS 2024 的论文
python -m crawler.dblp.batch_cli --db papers_test.db --conf CCS --year 2024 --limit 100 --verbose
```

### 调整请求间隔

```bash
# 避免 API 限流，增加请求间隔（默认 0.5 秒）
python -m crawler.dblp.batch_cli --db papers_test.db --limit 50 --delay 1.0 --verbose
```

> 注意：Semantic Scholar API 已有内置限流（1次/秒），无需额外 delay

## 4. 完整测试流程

```bash
# 步骤1: 初始化
python -c "from config import init_test_db; init_test_db()"

# 步骤2: 爬取论文
python -m crawler.dblp.cli CCS 2024 --db papers_test.db

# 步骤3: 验证数据
sqlite3 papers_test.db "SELECT COUNT(*) FROM papers"

# 步骤4: 获取摘要
python -m crawler.dblp.batch_cli --db papers_test.db --limit 10 --verbose
```

## 5. 验证摘要获取成功

```bash
# 查看有摘要的论文
sqlite3 papers_test.db "SELECT id, title, LENGTH(abstract) as len FROM papers WHERE abstract IS NOT NULL AND abstract != '' LIMIT 10"

# 查看摘要内容
sqlite3 papers_test.db "SELECT abstract FROM papers WHERE abstract IS NOT NULL AND abstract != '' LIMIT 1"
```
