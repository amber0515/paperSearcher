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
ENV_NAME = {"test": "TEST", "prod": "PROD"}.get(ENV, "UNKNOWN")


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
