# 基于 CCF 数据的 DBLP 论文爬取 - MVP 开发计划

## 目标

基于已爬取的 CCF 会议数据，实现按会议和年度维度爬取 DBLP 论文。

## 现状分析

### 已有资源
- **CCF 数据**：`ccf_venues` 表，633 条记录，包含 `abbreviation`、`dblp_url`、`ccf_rank`、`venue_type` 等字段
- **现有爬虫**：`crawler/` 模块已实现 DBLP 会议论文爬取
- **数据库**：`papers` 表已存在，可存储 76,000+ 篇论文

### 限制
- 现有爬虫仅支持 **21 个会议**，硬编码在 `DBLP_CONF_MAP` 中
- CCF 有 **58 个 A 类会议** + 更多 B/C 类

---

## MVP 方案：命令行参数式 CLI

### 核心特点
- **仅支持会议**（期刊留待后续）
- **命令行参数**驱动（非交互式）
- **每次指定年份**
- 从 CCF 数据库动态读取会议列表

---

## 使用示例

```bash
# 基础用法：爬取指定会议的某一年
python -m crawler.dblp_cli CCS 2024

# 批量爬取：多个会议
python -m crawler.dblp_cli CCS,SP,USS 2024

# 批量爬取：多个年份
python -m crawler.dblp_cli CCS 2022,2023,2024

# 组合：多个会议 + 多个年份
python -m crawler.dblp_cli CCS,SP,USS 2022,2023,2024

# 按 CCF 排名筛选：爬取所有 A 类安全会议
python -m crawler.dblp_cli --rank A --domain NIS 2024

# 指定数据库
python -m crawler.dblp_cli CCS 2024 --db papers_test.db

# 预览模式（不保存）
python -m crawler.dblp_cli CCS 2024 --preview-only
```

---

## 实现步骤

### Step 1: 创建 CLI 模块

**新建文件**：`crawler/dblp_cli.py`

```python
# 主要功能
1. 解析命令行参数
2. 从 ccf_venues 读取会议列表（venue_type='conference'）
3. 验证会议代码是否在 CCF 数据中
4. 复用现有 crawler.crawler 和 crawler.extractor
5. 保存到 papers 表
```

### Step 2: 扩展 DBLP URL 映射

**修改文件**：`crawler/config.py`

- 从 CCF 数据库读取 `dblp_url` 构建 URL
- 或扩展 `DBLP_CONF_MAP` 覆盖更多会议

### Step 3: 添加 CCF 筛选支持

**新建文件**：`crawler/dblp_cli.py`

- `--rank`：按 CCF 排名筛选（A/B/C）
- `--domain`：按领域筛选（AI/NIS/CN/...）

---

## 文件清单

| 操作 | 文件 | 功能 |
|------|------|------|
| **新建** | `crawler/dblp_cli.py` | CLI 入口，参数解析，调用爬虫 |
| **修改** | `crawler/config.py` | 扩展 DBLP_CONF_MAP 或动态读取 |
| **复用** | `crawler/crawler.py` | 爬虫核心逻辑 |
| **复用** | `crawler/extractor.py` | 数据提取 |
| **复用** | `crawler/ccf/database.py` | 读取 CCF 会议数据 |

---

## 关键文件路径

```
/Users/amber/dev_code/paperSearcher/
├── crawler/
│   ├── dblp_cli.py          # 新建：CLI 入口
│   ├── crawler.py           # 复用
│   ├── extractor.py         # 复用
│   ├── config.py            # 修改：扩展会议映射
│   └── main.py              # 参考
│
└── crawler/ccf/
    └── database.py          # 复用：读取 CCF 数据
```

---

## MVP 验证

完成后的测试步骤：

```bash
# 1. 测试单个会议单年
python -m crawler.dblp_cli CCS 2024

# 2. 测试批量爬取
python -m crawler.dblp_cli CCS,SP 2023,2024

# 3. 测试按排名筛选
python -m crawler.dblp_cli --rank A --domain NIS 2024

# 4. 验证数据库
python3 -c "import sqlite3; conn = sqlite3.connect('papers_test.db'); print(conn.execute('SELECT COUNT(*) FROM papers WHERE conference=\"CCS\" AND year=2024').fetchone()[0])"
```

---

## MVP 范围

| 功能 | 状态 |
|------|------|
| 会议爬取 | ✅ 包含 |
| 命令行参数 | ✅ 包含 |
| CCF 排名筛选 | ✅ 包含 |
| 领域筛选 | ✅ 包含 |
| 期刊爬取 | ❌ 后续 |
| 交互式 CLI | ❌ 不需要 |
| 摘要获取 | ❌ 后续 |
