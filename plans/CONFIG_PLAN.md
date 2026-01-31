# 配置管理方案 - 测试/生产环境切换

## 问题：当前项目配置问题

当前 `website.py` 中 `DB_PATH` 是硬编码的：
```python
DB_PATH = sys.path[0] + "/papers.db"  # 硬编码，无法切换环境
```

**风险**：
- 测试时会修改生产数据
- 无法方便地测试新功能
- 没有测试数据库

---

## 解决方案：统一配置管理

### 核心思路

1. **默认使用测试环境**（安全第一）
2. **通过环境变量切换到生产**
3. **清晰的启动提示**，当前使用哪个数据库

---

## 一、创建 `config.py` - 统一配置文件

```python
"""
项目配置 - 支持测试/生产环境切换
"""
import os
from pathlib import Path

# =============================================================================
# 环境配置
# =============================================================================

# 环境变量：ENV=test（测试）或 ENV=prod（生产）
# 默认使用测试环境（安全第一）
ENV = os.getenv("ENV", "test").lower()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 数据库路径配置
_DB_PATHS = {
    "test": PROJECT_ROOT / "papers_test.db",   # 测试数据库
    "prod": PROJECT_ROOT / "papers.db"          # 生产数据库
}

# 当前使用的数据库路径
DB_PATH = str(_DB_PATHS.get(ENV, _DB_PATHS["test"]))

# 环境标识（用于启动提示）
ENV_NAME = {"test": "🧪 测试环境", "prod": "🚀 生产环境"}.get(ENV, "❓ 未知环境")


def get_db_path(env: str = None) -> str:
    """
    获取数据库路径

    Args:
        env: 环境标识 ("test" 或 "prod")，默认使用当前环境

    Returns:
        str: 数据库文件路径
    """
    if env:
        return str(_DB_PATHS.get(env.lower(), _DB_PATHS["test"]))
    return DB_PATH


def init_test_db():
    """
    初始化测试数据库

    - 从生产数据库复制表结构
    - 或创建空表结构

    Returns:
        tuple: (success: bool, message: str)
    """
    import sqlite3

    test_db = _DB_PATHS["test"]
    prod_db = _DB_PATHS["prod"]

    # 如果测试数据库已存在，不覆盖
    if test_db.exists():
        return False, "测试数据库已存在"

    # 从生产数据库复制结构
    if prod_db.exists():
        import shutil
        shutil.copy2(prod_db, test_db)
        # 清空数据，只保留结构
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM papers")
        conn.commit()
        conn.close()
        return True, f"测试数据库已创建: {test_db}"

    # 如果生产数据库不存在，创建空表结构
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conference TEXT NOT NULL,
            year INTEGER NOT NULL,
            volume INTEGER,
            title TEXT NOT NULL UNIQUE,
            href TEXT,
            origin TEXT,
            abstract TEXT,
            bib TEXT,
            cat TEXT
        )
    """)
    conn.commit()
    conn.close()
    return True, f"测试数据库已创建: {test_db}"


# =============================================================================
# 业务配置
# =============================================================================

ALLOWED_CONFERENCES = {
    "ccs", "sp", "spw", "uss", "cest", "foci", "soups", "woot",
    "tdsc", "tifs", "ndss", "acsac", "csur", "comsur", "esorics",
    "csfw", "dsn", "compsec", "raid", "jcs", "tissec", "srds",
    "jsac", "tmc", "ton", "sigcomm", "mobicom", "infocom", "nsdi", "www"
}

MIN_YEAR, MAX_YEAR = 2016, 2025
MAX_KEYWORD_LENGTH = 200
MAX_LIMIT = 100
```

---

## 二、创建 `.env.example` - 环境变量模板

```bash
# 环境配置：test（测试）或 prod（生产）
# 默认：test
ENV=test
```

---

## 三、创建 `.gitignore` - 忽略配置文件

```gitignore
# 环境配置
.env

# 测试数据库
papers_test.db
```

---

## 四、修改 `website.py` - 使用新配置

### 修改 1：导入配置

在文件顶部，替换硬编码配置：

```python
# =============================================================================
# 配置常量
# =============================================================================

# 旧代码（删除）：
# DB_PATH = sys.path[0] + "/papers.db"
# ALLOWED_CONFERENCES = {...}
# MIN_YEAR, MAX_YEAR = 2016, 2025
# MAX_KEYWORD_LENGTH = 200
# MAX_LIMIT = 100

# 新代码（使用）：
from config import (
    DB_PATH,
    ALLOWED_CONFERENCES,
    MIN_YEAR,
    MAX_YEAR,
    MAX_KEYWORD_LENGTH,
    MAX_LIMIT,
    ENV_NAME
)
```

### 修改 2：添加启动提示

在 `if __name__ == '__main__'` 部分添加环境提示：

```python
if __name__ == '__main__':
    # 添加环境提示
    print(f"\n{'='*50}")
    print(f"Paper Searcher 启动中...")
    print(f"当前环境: {ENV_NAME}")
    print(f"数据库: {DB_PATH}")
    print(f"{'='*50}\n")

    try:
        host = sys.argv[1]
        port = sys.argv[2]
    except:
        host = '127.0.0.1'
        port = 5000

    app.run(host=host, port=port, debug=True)
```

---

## 五、使用方式

### 默认（测试环境）

```bash
# 不设置环境变量，默认使用测试环境
python3 website.py

# 输出：
# ==================================================
# Paper Searcher 启动中...
# 当前环境: 🧪 测试环境
# 数据库: /path/to/papers_test.db
# ==================================================
```

### 切换到生产环境

```bash
# 方式1: 环境变量
ENV=prod python3 website.py

# 输出：
# ==================================================
# Paper Searcher 启动中...
# 当前环境: 🚀 生产环境
# 数据库: /path/to/papers.db
# ==================================================

# 方式2: .env 文件
echo "ENV=prod" > .env
python3 website.py
```

### 首次使用：初始化测试数据库

```bash
# 方式1: Python 命令
python3 -c "from config import init_test_db; print(init_test_db()[1])"
# 输出: 测试数据库已创建: /path/to/papers_test.db

# 方式2: 交互式 Python
python3
>>> from config import init_test_db
>>> init_test_db()
(True, '测试数据库已创建: /path/to/papers_test.db')
```

---

## 六、文件清单

| 操作 | 文件 | 说明 |
|-----|------|------|
| **新建** | `config.py` | 统一配置文件 |
| **新建** | `.env.example` | 环境变量模板 |
| **新建** | `.gitignore` | 忽略配置和测试数据库 |
| **修改** | `website.py` | 使用新配置，添加环境提示 |

---

## 七、安全检查

### 启动前检查

建议在启动时添加检查，防止误操作：

```python
# 在 website.py 的 main 函数中添加
if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"Paper Searcher 启动中...")
    print(f"当前环境: {ENV_NAME}")
    print(f"数据库: {DB_PATH}")

    # 安全检查：如果是生产环境，要求确认
    if ENV == "prod" and "--auto" not in sys.argv:
        response = input("\n⚠️  即将连接生产数据库，确认继续？(y/N): ")
        if response.lower() != 'y':
            print("已取消启动")
            sys.exit(0)

    print(f"{'='*50}\n")

    # ... 原有启动代码
```

---

## 八、总结

### 效果

| 场景 | 命令 | 使用的数据库 |
|-----|------|------------|
| 开发测试 | `python3 website.py` | `papers_test.db` 🧪 |
| 生产运行 | `ENV=prod python3 website.py` | `papers.db` 🚀 |

### 优势

- ✅ **默认安全**：不设置环境变量时，默认使用测试数据库
- ✅ **清晰提示**：启动时显示当前环境和数据库路径
- ✅ **方便切换**：通过环境变量轻松切换
- ✅ **配置集中**：所有配置在 `config.py` 中管理
