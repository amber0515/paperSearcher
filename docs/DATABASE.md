# 数据库设计文档

## 概述

Paper Searcher 使用 SQLite 数据库存储网络安全和计算机网络领域的学术论文数据。数据库包含来自顶级会议和期刊的论文信息，支持关键词搜索、会议筛选和年份筛选等功能。

## 数据库文件

| 文件 | 说明 |
|------|------|
| `papers.db` | 生产数据库（约 154 MB，76,442 篇论文） |
| `papers.db.zip` | 压缩备份文件（约 42 MB） |
| `papers_test.db` | 测试环境数据库（与生产数据库同构） |

## 表结构

### papers 表

论文信息的主表，存储所有论文的基本元数据和摘要。

```sql
CREATE TABLE papers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    conference  TEXT    NOT NULL,
    year        INTEGER NOT NULL,
    volume      INTEGER,
    title       TEXT    NOT NULL UNIQUE,
    href        TEXT,
    origin      TEXT,
    abstract    TEXT,
    bib         TEXT,
    cat         TEXT
);
```

### 字段说明

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 论文唯一标识符 |
| `conference` | TEXT | NOT NULL | 会议/期刊简称（如 CCS、S&P、NDSS） |
| `year` | INTEGER | NOT NULL | 发表年份 |
| `volume` | INTEGER | - | 卷号 |
| `title` | TEXT | NOT NULL UNIQUE | 论文标题（唯一） |
| `href` | TEXT | - | 论文链接 URL |
| `origin` | TEXT | - | 来源信息 |
| `abstract` | TEXT | - | 论文摘要 |
| `bib` | TEXT | - | BibTeX 引用格式 |
| `cat` | TEXT | - | 分类标签 |

## 支持的会议/期刊

系统支持以下 28 个会议和期刊：

### 安全领域
| 简称 | 全称 |
|------|------|
| CCS | ACM Conference on Computer and Communications Security |
| S&P / SP | IEEE Symposium on Security and Privacy |
| NDSS | Network and Distributed System Security Symposium |
| USENIX Security / USS | USENIX Security Symposium |
| ACSAC | Annual Computer Security Applications Conference |
| ESORICS | European Symposium on Research in Computer Security and Privacy |
| CSFW | IEEE Computer Security Foundations Workshop |
| RAID | Recent Advances in Intrusion Detection |
| S&P Workshops / SPW | IEEE S&P Workshops |
| USENIX Security Workshops / CEST | USENIX Security Workshops |
| FO CI | IEEE Conference on Decision and Control (相关) |
| SOUPS | Symposium On Usable Privacy and Security |
| WOOT | Workshop on Offensive Technologies |

### 期刊
| 简称 | 全称 |
|------|------|
| TDSC | IEEE Transactions on Dependable and Secure Computing |
| TIFS | IEEE Transactions on Information Forensics and Security |
| TISSEC | ACM Transactions on Information and System Security |
| TMC | IEEE Transactions on Mobile Computing |
| TON | IEEE/ACM Transactions on Networking |
| JSAC | IEEE Journal on Selected Areas in Communications |
| CSUR | ACM Computing Surveys |
| COMSUR | ACM Communications Surveys and Tutorials |
| COMPSEC | Computers & Security |
| JCS | Journal of Computer Security |
| SRDS | IEEE Symposium on Reliable Distributed Systems |
| DSN | IEEE/IFIP International Conference on Dependable Systems and Networks |

### 计算机网络领域
| 简称 | 全称 |
|------|------|
| SIGCOMM | ACM SIGCOMM Conference |
| MobiCom | ACM International Conference on Mobile Computing and Networking |
| NSDI | Symposium on Networked Systems Design and Implementation |
| INFOCOM | IEEE International Conference on Computer Communications |
| WWW | The Web Conference |

## 数据统计

### 论文总数
**76,442** 篇论文

### 按会议/期刊分布（前 15）

| 会议/期刊 | 论文数量 |
|-----------|----------|
| NIPS | 16,526 |
| AAAI | 15,159 |
| ICML | 8,711 |
| TMC | 3,645 |
| TIFS | 3,517 |
| WWW | 3,200 |
| COMPSEC | 2,865 |
| INFOCOM | 2,666 |
| JSAC | 2,347 |
| TON | 2,130 |
| TDSC | 1,899 |
| CCS | 1,895 |
| USS | 1,873 |
| CSUR | 1,686 |
| S&P | 1,339 |

### 按年份分布

| 年份 | 论文数量 |
|------|----------|
| 2025 | 6,932 |
| 2024 | 16,139 |
| 2023 | 12,234 |
| 2022 | 9,545 |
| 2021 | 9,068 |
| 2020 | 7,879 |
| 2019 | 6,555 |
| 2018 | 2,832 |
| 2017 | 2,650 |
| 2016 | 2,608 |

## 环境配置

项目支持测试和生产两种环境，通过环境变量 `ENV` 控制：

```bash
# 测试环境（默认）
ENV=test python3 website.py

# 生产环境
ENV=prod python3 website.py
```

| 环境 | 数据库文件 | 说明 |
|------|------------|------|
| TEST | `papers_test.db` | 默认环境，用于开发和测试 |
| PROD | `papers.db` | 生产环境，启动前需确认 |

## 查询示例

### 基本搜索
```sql
-- 在标题或摘要中搜索关键词
SELECT * FROM papers WHERE title LIKE '%blockchain%' OR abstract LIKE '%blockchain%';
```

### 组合搜索（AND）
```sql
-- 同时包含两个关键词
SELECT * FROM papers WHERE (title LIKE '%blockchain%' AND title LIKE '%security%')
   OR (abstract LIKE '%blockchain%' AND abstract LIKE '%security%');
```

### 筛选会议和年份
```sql
-- 按会议和年份筛选
SELECT * FROM papers WHERE conference IN ('CCS', 'S&P') AND year IN (2023, 2024);
```

### 分页查询
```sql
-- 分页获取结果（每页 10 条，第 2 页）
SELECT * FROM papers WHERE title LIKE '%security%' OR abstract LIKE '%security%'
ORDER BY year DESC LIMIT 10 OFFSET 10;
```

## API 接口

### 搜索接口
- **端点**: `GET /search`
- **参数**:
  - `q`: 搜索关键词（支持 `+` 表示 AND，`|` 表示 OR）
  - `s`: 会议筛选（逗号分隔，如 `ccs,sp`）
  - `y`: 年份筛选（逗号分隔，如 `2023,2024`）
  - `offset`: 分页偏移量（默认 0）
  - `limit`: 每页数量（默认 10，最大 100）

### 摘要接口
- **端点**: `GET /abstract/<paper_id>`
- **参数**:
  - `paper_id`: 论文 ID

## 注意事项

1. **安全性**: 数据库使用参数化查询，防止 SQL 注入攻击
2. **唯一性**: `title` 字段设置了 UNIQUE 约束，确保不重复收录
3. **索引**: 建议为 `conference`、`year` 字段添加索引以提高查询性能
4. **备份**: 定期备份 `papers.db.zip` 压缩文件

## 扩展建议

如需扩展数据库功能，可考虑：

1. 添加全文搜索索引（FTS5）
2. 添加作者信息表和关联关系
3. 添加引用/被引用关系
4. 添加论文下载状态跟踪
5. 添加用户收藏和标签功能
