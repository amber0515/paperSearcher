# Paper Searcher - 后端服务
# 功能：提供论文搜索 API，支持关键词、会议、年份筛选

import sys
import re
from flask import Flask, request, jsonify
import sqlite3
import json

app = Flask(__name__)


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
def build_search_query(keywords, operators, source_list=None, year_list=None):
    """
    构建参数化查询的 SQL 模板和参数列表

    Args:
        keywords: 关键词列表
        operators: 运算符列表 ("and" 或 "or")
        source_list: 会议筛选列表（如 ["ccs", "sp"]）
        year_list: 年份筛选列表（如 [2022, 2023]）

    Returns:
        (sql_template, params): SQL 模板（带 ? 占位符）和参数值列表
    """
    params = []

    # 构建 title 部分的条件
    title_conditions = []
    for kw in keywords:
        title_conditions.append("title LIKE ?")
        params.append(f"%{kw}%")

    # 用运算符连接
    title_clause = ""
    for i in range(len(operators)):
        title_clause += title_conditions[i] + " "
        title_clause += operators[i] + " "
    title_clause += title_conditions[-1] if title_conditions else "1=1"

    # 构建 abstract 部分的条件
    abstract_conditions = []
    for kw in keywords:
        abstract_conditions.append("abstract LIKE ?")
        params.append(f"%{kw}%")

    abstract_clause = ""
    for i in range(len(operators)):
        abstract_clause += abstract_conditions[i] + " "
        abstract_clause += operators[i] + " "
    abstract_clause += abstract_conditions[-1] if abstract_conditions else "1=1"

    # 组合：title 部分和 abstract 部分用 OR 连接
    sql = f"(({title_clause}) OR ({abstract_clause}))"

    # 添加 conference 筛选
    if source_list:
        placeholders = ",".join(["?" for _ in source_list])
        sql += f" AND conference IN ({placeholders})"
        params.extend(source_list)

    # 添加 year 筛选
    if year_list:
        placeholders = ",".join(["?" for _ in year_list])
        sql += f" AND year IN ({placeholders})"
        params.extend(year_list)

    return sql, params


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
    # 验证关键词：只允许字母、数字、空格、+、|、中文字符
    if not re.match(r'^[\w\s\+\|\u4e00-\u9fff]+$', q):
        return json.dumps({"code": 1, "msg": "Invalid keyword format"})
    if len(q) > 200:
        return json.dumps({"code": 1, "msg": "Keyword too long"})

    # 验证 offset/limit：必须是正整数
    try:
        offset = max(0, int(offset))
        limit = min(100, int(limit))  # 最多 100 条
    except ValueError:
        return json.dumps({"code": 1, "msg": "Invalid offset/limit"})

    # 验证 source：白名单检查
    ALLOWED_CONFERENCES = {
        "ccs", "sp", "spw", "uss", "cest", "foci", "soups", "woot",
        "tdsc", "tifs", "ndss", "acsac", "csur", "comsur", "esorics",
        "csfw", "dsn", "compsec", "raid", "jcs", "tissec", "srds",
        "jsac", "tmc", "ton", "sigcomm", "mobicom", "infocom", "nsdi", "www"
    }
    source_list = None
    if source:
        source_list = [s.strip().lower() for s in source.split(",")]
        if not set(source_list).issubset(ALLOWED_CONFERENCES):
            return json.dumps({"code": 1, "msg": "Invalid conference"})
        # 转换为大写，因为数据库中存储的是大写
        source_list = [s.upper() for s in source_list]

    # 验证 year：必须是 4 位数字，范围 2016-2025
    year_list = None
    if year:
        year_list = []
        for y in year.split(","):
            if not y.isdigit() or len(y) != 4:
                return json.dumps({"code": 1, "msg": "Invalid year format"})
            y_int = int(y)
            if y_int < 2016 or y_int > 2025:
                return json.dumps({"code": 1, "msg": "Year out of range"})
            year_list.append(y_int)

    # ========== 构建并执行查询 ==========
    conn = sqlite3.connect(sys.path[0] + "/papers.db")
    c = conn.cursor()

    try:
        # 解析关键词
        keywords, operators = parse_keywords(q)

        # 构建 SQL 模板和参数
        where_clause, params = build_search_query(keywords, operators, source_list, year_list)

        # 查询总数
        count_sql = f"SELECT COUNT(*) FROM papers WHERE {where_clause}"
        cursor = c.execute(count_sql, params)
        total = cursor.fetchone()[0]

        # 查询数据
        data_sql = f"SELECT * FROM papers WHERE {where_clause} ORDER BY year DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor = c.execute(data_sql, params)

        # 将查询结果转换为字典列表
        key_list = ["id", "conference", "year", "volume", "title",
                    "href", "origin", "abstract", "bib", "cat"]
        results = [dict(zip(key_list, row)) for row in cursor]

        msg = {"code": 0, "msg": "success", "rows": results, "total": total}

    except sqlite3.Error as e:
        msg = {"code": 1, "msg": str(e)}
    finally:
        conn.close()

    return json.dumps(msg)


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

    conn = sqlite3.connect(sys.path[0] + "/papers.db")
    c = conn.cursor()

    try:
        # 参数化查询
        cursor = c.execute(
            "SELECT title, abstract FROM papers WHERE id=?",
            (paper_id,)
        )
        results = list(cursor)
        msg = {"code": 0, "msg": "success", "data": results}
    except sqlite3.Error as e:
        msg = {"code": 1, "msg": str(e)}
    finally:
        conn.close()

    return json.dumps(msg)


if __name__ == '__main__':
    try:
        host = sys.argv[1]
        port = sys.argv[2]
    except:
        host = '127.0.0.1'
        port = 5000

    # debug=True 会自动重载代码，并显示详细错误信息
    app.run(host=host, port=port, debug=True)
