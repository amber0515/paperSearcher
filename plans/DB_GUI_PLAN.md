# SQLite 数据库 GUI 管理方案

## 数据库基本信息

- **数据库文件**: `papers.db` (生产环境) / `papers_test.db` (测试环境)
- **表结构**: `papers` 表包含 9 个字段（id, conference, year, volume, title, href, origin, abstract, bib, cat）
- **数据量**: 约 76,442 篇论文

---

## 推荐工具 (按优先级)

### 1. DB Browser for SQLite (首选 - 免费、功能全面)

**下载**: https://sqlitebrowser.org/

**安装**:
```bash
# macOS (使用 Homebrew)
brew install --cask db-browser-for-sqlite

# 或直接下载 .dmg 文件安装
```

**主要功能**:
- 浏览数据: 可视化表格视图，支持排序、筛选
- 执行 SQL: 内置 SQL 编辑器，支持语法高亮
- 编辑数据: 直接修改、添加、删除记录
- 导入/导出: 支持 CSV、JSON、SQL 格式
- 查看表结构: 图形化显示 schema、索引

---

### 2. TablePlus (macOS 优选 - 现代 UI)

**下载**: https://tableplus.com/

**安装**:
```bash
# macOS (使用 Homebrew)
brew install --cask tableplus
```

**特点**:
- 现代简洁的界面
- 多数据库支持
- 快捷键丰富
- 支持多个数据库连接

---

### 3. DBeaver (开源 - 功能强大)

**下载**: https://dbeaver.io/

**安装**:
```bash
# macOS (使用 Homebrew)
brew install --cask dbeaver-community
```

**特点**:
- 完全免费开源
- 支持 80+ 种数据库
- ER 图功能
- 数据迁移工具

---

## 常用操作速查

### 打开数据库
1. 启动工具
2. 选择 "Open Database" 或 "Open File"
3. 选择 `papers.db` 文件

### 常用 SQL 查询
```sql
-- 统计各会议论文数
SELECT conference, COUNT(*) as count
FROM papers
GROUP BY conference
ORDER BY count DESC;

-- 统计各年份论文数
SELECT year, COUNT(*) as count
FROM papers
GROUP BY year
ORDER BY year DESC;

-- 查找特定会议的论文
SELECT * FROM papers WHERE conference = 'CCS' ORDER BY year DESC;

-- 搜索包含关键词的论文
SELECT title, conference, year, href
FROM papers
WHERE title LIKE '%machine learning%'
   OR abstract LIKE '%machine learning%'
LIMIT 20;

-- 查看最新论文
SELECT * FROM papers ORDER BY year DESC, id DESC LIMIT 10;

-- 组合筛选 (会议 + 年份)
SELECT * FROM papers
WHERE conference IN ('CCS', 'S&P', 'NDSS', 'USENIX Security')
  AND year >= 2020
ORDER BY year DESC;
```

---

## 无需代码修改

此方案不需要对现有代码进行任何修改，只需：
1. 安装 GUI 工具
2. 用工具打开 `papers.db` 即可查看和管理数据
