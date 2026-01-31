# Paper Searcher - 后端服务
# 功能：提供论文搜索 API，支持关键词、会议、年份筛选

import sys
import re
import contextlib
from flask import Flask, request, jsonify
import sqlite3
import json

app = Flask(__name__)

# =============================================================================
# 配置常量（从 config.py 导入）
# =============================================================================
from config import (
    DB_PATH,
    ALLOWED_CONFERENCES,
    MIN_YEAR,
    MAX_YEAR,
    MAX_KEYWORD_LENGTH,
    MAX_LIMIT,
    ENV_NAME
)


# =============================================================================
# 关键词解析函数（只解析，不构建 SQL）
# =============================================================================
def parse_keywords(q):
    """
    解析搜索关键词，返回 (关键词列表, 运算符列表)

    搜索语法：
    - 使用 + 分隔表示 AND（两个关键词都必须存在）
    - 使用 | 分隔表示 OR（任一关键词存在即可）
    - 示例：
      - "blockchain+security" → (["blockchain", "security"], ["and"])
      - "security|iot"        → (["security", "iot"], ["or"])

    Args:
        q: 用户输入的搜索关键词字符串

    Returns:
        (keywords, operators): 关键词列表和运算符列表
    """
    keywords = []
    operator = []
    tmp = []

    i = 0
    finish_flag = False
    while i <= len(q):
        if i == len(q):
            finish_flag = True
        elif q[i] == "+":
            operator.append("and")
            finish_flag = True
        elif q[i] == "|":
            operator.append("or")
            finish_flag = True
        else:
            tmp.append(q[i])

        if finish_flag:
            tmp_str = "".join(tmp).strip()
            if tmp_str:
                keywords.append(tmp_str)
            tmp = []
            finish_flag = False
        i += 1

    return keywords, operator


# =============================================================================
# 构建参数化查询函数
# =============================================================================
def _build_like_conditions(keywords, operators, field_name):
    """
    构建 LIKE 条件子句（内部辅助函数）

    Args:
        keywords: 关键词列表
        operators: 运算符列表 ("and" 或 "or")
        field_name: 字段名（如 "title" 或 "abstract"）

    Returns:
        (clause, params): 条件子句和参数列表
    """
    params = []
    conditions = []

    for kw in keywords:
        conditions.append(f"{field_name} LIKE ?")
        params.append(f"%{kw}%")

    # 用运算符连接条件
    clause_parts = []
    for i in range(len(operators)):
        clause_parts.append(conditions[i])
        clause_parts.append(operators[i])
    if conditions:
        clause_parts.append(conditions[-1])

    clause = " ".join(clause_parts) if conditions else "1=1"
    return clause, params


def build_search_query(keywords, operators, source_list=None, year_list=None):
    """
    构建参数化查询的 SQL 模板和参数列表

    Args:
        keywords: 关键词列表
        operators: 运算符列表 ("and" 或 "or")
        source_list: 会议筛选列表（如 ["CCS", "SP"]）
        year_list: 年份筛选列表（如 [2022, 2023]）

    Returns:
        (sql_template, params): SQL 模板（带 ? 占位符）和参数值列表
    """
    all_params = []

    # 构建 title 部分的条件
    title_clause, title_params = _build_like_conditions(keywords, operators, "title")

    # 构建 abstract 部分的条件
    abstract_clause, abstract_params = _build_like_conditions(keywords, operators, "abstract")

    # 组合：title 部分和 abstract 部分用 OR 连接
    sql = f"(({title_clause}) OR ({abstract_clause}))"
    all_params.extend(title_params)
    all_params.extend(abstract_params)

    # 添加 conference 筛选
    if source_list:
        placeholders = ",".join(["?" for _ in source_list])
        sql += f" AND conference IN ({placeholders})"
        all_params.extend(source_list)

    # 添加 year 筛选
    if year_list:
        placeholders = ",".join(["?" for _ in year_list])
        sql += f" AND year IN ({placeholders})"
        all_params.extend(year_list)

    return sql, all_params


# =============================================================================
# 输入验证函数
# =============================================================================
def validate_keyword(q: str):
    """
    验证关键词格式

    Args:
        q: 用户输入的关键词字符串

    Returns:
        None 表示验证通过，否则返回错误消息字符串
    """
    if not q:
        return None  # 空关键词允许
    if not re.match(r'^[\w\s\+\|\u4e00-\u9fff]+$', q):
        return "Invalid keyword format"
    if len(q) > MAX_KEYWORD_LENGTH:
        return "Keyword too long"
    return None


def validate_pagination(offset: str, limit: str):
    """
    验证分页参数

    Args:
        offset: 偏移量字符串
        limit: 每页数量字符串

    Returns:
        (offset, limit) 元组表示验证通过，None 表示验证失败
    """
    try:
        offset_int = max(0, int(offset))
        limit_int = min(MAX_LIMIT, int(limit))
        return offset_int, limit_int
    except ValueError:
        return None


def validate_conferences(source: str):
    """
    验证会议筛选参数

    Args:
        source: 逗号分隔的会议字符串（如 "ccs,sp"）

    Returns:
        大写会议列表表示验证通过，None 表示验证失败
    """
    if not source:
        return None
    source_list = [s.strip().lower() for s in source.split(",")]
    if not set(source_list).issubset(ALLOWED_CONFERENCES):
        return None  # 无效会议
    return [s.upper() for s in source_list]  # 转换为大写


def validate_years(year: str):
    """
    验证年份筛选参数

    Args:
        year: 逗号分隔的年份字符串（如 "2022,2023"）

    Returns:
        年份整数列表表示验证通过，None 表示验证失败
    """
    if not year:
        return None
    year_list = []
    for y in year.split(","):
        if not y.isdigit() or len(y) != 4:
            return None
        y_int = int(y)
        if y_int < MIN_YEAR or y_int > MAX_YEAR:
            return None
        year_list.append(y_int)
    return year_list


# =============================================================================
# 数据库函数
# =============================================================================
@contextlib.contextmanager
def get_db_connection():
    """
    数据库连接上下文管理器

    Usage:
        with get_db_connection() as (conn, cursor):
            cursor.execute(...)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        yield conn, cursor
    finally:
        conn.close()


def search_papers(where_clause: str, params: list, limit: int, offset: int):
    """
    执行论文搜索查询

    Args:
        where_clause: WHERE 子句
        params: SQL 参数列表
        limit: 每页数量
        offset: 偏移量

    Returns:
        {"code": 0/1, "msg": "...", "rows": [...], "total": ...}
    """
    try:
        with get_db_connection() as (conn, cursor):
            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM papers WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]

            # 查询数据
            data_sql = f"SELECT * FROM papers WHERE {where_clause} ORDER BY year DESC LIMIT ? OFFSET ?"
            cursor.execute(data_sql, params + [limit, offset])

            # 将查询结果转换为字典列表
            key_list = ["id", "conference", "year", "volume", "title",
                        "href", "origin", "abstract", "bib", "cat"]
            results = [dict(zip(key_list, row)) for row in cursor]

            return {"code": 0, "msg": "success", "rows": results, "total": total}

    except sqlite3.Error as e:
        return {"code": 1, "msg": str(e)}


def get_paper_abstract(paper_id: int):
    """
    获取指定论文的标题和摘要

    Args:
        paper_id: 论文 ID

    Returns:
        {"code": 0/1, "msg": "...", "data": [[title, abstract]]}
    """
    try:
        with get_db_connection() as (conn, cursor):
            cursor.execute(
                "SELECT title, abstract FROM papers WHERE id=?",
                (paper_id,)
            )
            results = list(cursor)
            return {"code": 0, "msg": "success", "data": results}
    except sqlite3.Error as e:
        return {"code": 1, "msg": str(e)}


# =============================================================================
# 路由：首页
# =============================================================================
@app.route('/')
def home():
    """返回首页（静态 HTML 文件）"""
    return app.send_static_file('index.html')


# =============================================================================
# 路由：搜索接口（已修复 SQL 注入）
# =============================================================================
@app.route('/search')
def get_info():
    """
    论文搜索 API（使用参数化查询，防止 SQL 注入）

    请求参数：
    - q: 搜索关键词（支持 + 和 | 运算符）
    - s: 会议筛选（可选，如 "ccs,sp"）
    - y: 年份筛选（可选，如 "2022,2023"）
    - offset: 分页偏移量
    - limit: 每页数量

    返回 JSON：
    {
        "code": 0,           # 0=成功, 1=失败
        "msg": "success",
        "rows": [...],       # 论文列表
        "total": 123         # 总数
    }
    """
    # 获取请求参数
    q = request.args.get("q", "")
    source = request.args.get("s")
    year = request.args.get("y")
    offset = request.args.get("offset", "0")
    limit = request.args.get("limit", "10")

    # ========== 输入验证 ==========
    error = validate_keyword(q)
    if error:
        return json.dumps({"code": 1, "msg": error})

    pagination = validate_pagination(offset, limit)
    if not pagination:
        return json.dumps({"code": 1, "msg": "Invalid offset/limit"})
    offset, limit = pagination

    source_list = validate_conferences(source)
    if source == "" or (source and source_list is None):
        return json.dumps({"code": 1, "msg": "Invalid conference"})

    year_list = validate_years(year)
    if year == "" or (year and year_list is None):
        return json.dumps({"code": 1, "msg": "Invalid year format"})

    # ========== 构建并执行查询 ==========
    keywords, operators = parse_keywords(q)
    where_clause, params = build_search_query(keywords, operators, source_list, year_list)
    result = search_papers(where_clause, params, limit, offset)

    return json.dumps(result)


# =============================================================================
# 路由：获取论文摘要（已修复 SQL 注入）
# =============================================================================
@app.route('/abstract/<q>')
def get_abs(q):
    """
    获取指定论文的标题和摘要（使用参数化查询，防止 SQL 注入）

    参数：
    - q: 论文 ID

    返回 JSON：
    {
        "code": 0,
        "msg": "success",
        "data": [[title, abstract]]
    }
    """
    # 验证 id 是正整数
    try:
        paper_id = int(q)
        if paper_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return json.dumps({"code": 1, "msg": "Invalid paper id"})

    result = get_paper_abstract(paper_id)
    return json.dumps(result)


if __name__ == '__main__':
    # 如果是测试环境且数据库不存在，自动创建
    if ENV_NAME == "TEST":
        from config import init_test_db
        success, msg = init_test_db()
        if success:
            print(f"提示: {msg}")

    # 添加环境提示
    print(f"\n{'='*50}")
    print(f"Paper Searcher 启动中...")
    print(f"当前环境: [{ENV_NAME}]")
    print(f"数据库: {DB_PATH}")
    print(f"{'='*50}")

    # 安全检查：如果是生产环境，要求确认
    if ENV_NAME == "PROD" and "--auto" not in sys.argv:
        response = input("\n即将连接生产数据库，确认继续？(y/N): ")
        if response.lower() != 'y':
            print("已取消启动")
            sys.exit(0)
    print()

    try:
        host = sys.argv[1]
        port = sys.argv[2]
    except:
        host = '127.0.0.1'
        port = 5000

    # debug=True 会自动重载代码，并显示详细错误信息
    app.run(host=host, port=port, debug=True)
