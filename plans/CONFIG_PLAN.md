# 配置管理 - 测试/生产环境切换

## 功能概述

项目已实现测试/生产环境切换功能，通过 `config.py` 统一管理配置。

**核心特点**：
- 默认使用测试环境（安全第一）
- 通过环境变量切换到生产
- 启动时清晰显示当前环境和数据库路径
- 生产环境启动需确认

## 使用方式

### 测试环境（默认）

```bash
python3 website.py
```

输出：
```
==================================================
Paper Searcher 启动中...
当前环境: 🧪 TEST
数据库: /path/to/papers_test.db
==================================================
```

### 生产环境

```bash
# 方式1: 环境变量
ENV=prod python3 website.py

# 方式2: .env 文件
echo "ENV=prod" > .env
python3 website.py
```

启动时需要确认：
```
==================================================
Paper Searcher 启动中...
当前环境: 🚀 PROD
数据库: /path/to/papers.db
==================================================

⚠️  即将连接生产数据库，确认继续？(y/N):
```

### 自定义 host/port

```bash
python3 website.py 0.0.0.0 8080
```

## 配置说明

### 环境变量

| 变量 | 可选值 | 默认值 | 说明 |
|-----|-------|-------|------|
| `ENV` | `test`, `prod` | `test` | 运行环境 |

### 数据库路径

| 环境 | 数据库文件 | 说明 |
|-----|----------|------|
| 测试 | `papers_test.db` | 测试开发，数据可随意修改 |
| 生产 | `papers.db` | 正式运行，76,000+ 篇论文 |

### 业务配置常量

- `ALLOWED_CONFERENCES`: 28 个支持的会议
- `MIN_YEAR`, `MAX_YEAR`: 2016-2025
- `MAX_KEYWORD_LENGTH`: 200 字符
- `MAX_LIMIT`: 每页最多 100 篇论文

## 首次使用

### 初始化测试数据库

```bash
python3 -c "from config import init_test_db; print(init_test_db()[1])"
```

### 创建 .env 文件

```bash
cp .env.example .env
# 编辑 .env 设置 ENV=test 或 ENV=prod
```

## 安全注意事项

- 建议仅在本地 (`127.0.0.1`) 运行
- 测试环境不会修改生产数据
- 生产环境启动需要手动确认
- `.env` 和 `papers_test.db` 已在 `.gitignore` 中排除

## 相关文件

- [config.py](../config.py) - 配置文件
- [.env.example](../.env.example) - 环境变量模板
- [website.py](../website.py) - 使用配置的主程序
