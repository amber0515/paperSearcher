# CCF 会议/期刊收录计划

## 目标
将 CCF 认定的全部会议和期刊（约 394 个会议 + 大量期刊）收录到数据库中，作为后续论文管理的索引依据。

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

| 代码 | 领域 |
|------|------|
| ARCH | 计算机体系结构/并行与分布计算/存储系统 |
| CN | 计算机网络 |
| NIS | 网络与信息安全 |
| SE | 软件工程/系统软件/程序设计语言 |
| DB | 数据库/数据挖掘/内容检索 |
| TC | 计算机科学理论 |
| GM | 计算机图形学与多媒体 |
| AI | 人工智能 |
| HCIAndPC | 人机交互与普适计算 |
| Cross_Compre_Emerging | 交叉/综合/新兴 |

---

## 爬虫实现

### 数据源
- **主数据源**: https://ccf.atom.im/ (单页面，结构化数据，易于解析)
- **备用数据源**: https://www.ccf.org.cn/Academic_Evaluation/By_category/

### 新建文件

| 文件 | 功能 |
|------|------|
| `crawler/ccf_crawler.py` | 抓取 CCF 网站数据 |
| `crawler/ccf_parser.py` | 解析 HTML 表格数据 |
| `crawler/ccf_db.py` | 数据库操作 (保存/查询) |
| `crawler/ccf_cli.py` | 命令行接口 |

### CLI 使用方式

```bash
# 预览数据（不保存）
python -m crawler.ccf_cli --preview-only --preview 20

# 完整抓取并保存到测试数据库
python -m crawler.ccf_cli --db papers_test.db

# 完整抓取并保存到生产数据库
python -m crawler.ccf_cli
```

---

## 后端 API 扩展

### 新增接口

| 接口 | 功能 |
|------|------|
| `GET /api/ccf/venues` | 获取 CCF 会议/期刊列表 (支持 rank/type/domain 筛选) |
| `GET /api/ccf/domains` | 获取各领域统计信息 |

### 搜索集成

修改 `/search` 接口，新增 `ccf_rank` 参数支持按等级筛选：
```
/search?q=security&ccf_rank=A
```

---

## 修改的现有文件

| 文件 | 修改内容 |
|------|----------|
| `config.py` | 添加 CCF_DOMAINS, CCF_RANKS 等配置 |
| `website.py` | 添加 CCF API 接口，支持 CCF 等级筛选 |

---

## 实现步骤

### Phase 1: 数据库 (1-2 小时)
- [ ] 创建 `ccf_venues` 表及索引
- [ ] 创建数据库迁移脚本

### Phase 2: 爬虫 (2-3 小时)
- [ ] 实现 `ccf_crawler.py` - 抓取网页
- [ ] 实现 `ccf_parser.py` - 解析数据
- [ ] 实现 `ccf_db.py` - 存储数据
- [ ] 实现 `ccf_cli.py` - CLI 工具
- [ ] 测试爬虫

### Phase 3: 后端集成 (2-3 小时)
- [ ] 更新 `config.py` 添加 CCF 配置
- [ ] 实现 `/api/ccf/venues` 接口
- [ ] 实现 `/api/ccf/domains` 接口
- [ ] 修改 `/search` 接口支持 CCF 筛选
- [ ] 测试 API

### Phase 4: 数据导入 (1 小时)
- [ ] 运行爬虫填充数据
- [ ] 验证数据完整性

### Phase 5: 测试验证 (1 小时)
- [ ] SQL 验证查询
- [ ] API 接口测试
- [ ] 端到端测试

---

## 验证方法

### SQL 验证
```sql
-- 检查各领域会议数量
SELECT domain, COUNT(*) FROM ccf_venues GROUP BY domain;

-- 检查等级分布
SELECT ccf_rank, venue_type, COUNT(*) FROM ccf_venues GROUP BY ccf_rank, venue_type;

-- 验证已知会议
SELECT * FROM ccf_venues WHERE abbreviation IN ('CCS', 'SIGCOMM', 'NeurIPS');
```

### API 测试
```bash
curl "http://localhost:5000/api/ccf/venues?rank=A&type=conference"
curl "http://localhost:5000/api/ccf/domains"
```

---

## 关键文件清单

### 新建文件
- `crawler/ccf_crawler.py`
- `crawler/ccf_parser.py`
- `crawler/ccf_db.py`
- `crawler/ccf_cli.py`
- `migrations/add_ccf_venues.sql`

### 修改文件
- `config.py`
- `website.py`
