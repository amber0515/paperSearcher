# Paper Searcher - 后端服务
# 功能：提供论文搜索 API，支持关键词、会议、年份筛选

import sys
from flask import Flask, request, jsonify
import sqlite3
import json

app = Flask(__name__)


# =============================================================================
# SQL 注入"防护"函数（存在安全隐患，仅作注释说明）
# =============================================================================
def sqlinjection(keyword):
    """
    尝试转义特殊字符以防止 SQL 注入
    ⚠️ 警告：这种方式无法真正防止 SQL 注入！

    原理：在 SQL 中，单引号 ' 用于界定字符串。通过将 ' 替换为 ''（两个单引号），
    SQL 会将其视为字符串内的单引号而非字符串结束符。

    问题：
    1. 只处理了部分特殊字符，还有其他绕过方式
    2. 使用字符串拼接构建 SQL，即使转义也可能被绕过
    3. 正确做法应使用参数化查询（prepared statements）

    Args:
        keyword: 用户输入的关键词

    Returns:
        转义后的字符串
    """
    if keyword:
        keyword = keyword.replace("/", "//")
        keyword = keyword.replace("'", "''")   # 单引号转义为双单引号
        keyword = keyword.replace("[", "/[")
        keyword = keyword.replace("]", "/]")
        keyword = keyword.replace("%", "/%")   # % 是 LIKE 通配符
        keyword = keyword.replace("&", "/&")
        keyword = keyword.replace("_", "/_")   # _ 是 LIKE 单字符通配符
        keyword = keyword.replace("(", "/(")
        keyword = keyword.replace(")", "/)")
    return keyword


# =============================================================================
# 关键词解析与 SQL 查询构建函数（核心搜索逻辑）
# =============================================================================
def keywords(q, source, year, page):
    """
    解析用户搜索关键词，构建 SQL WHERE 子句

    搜索语法：
    - 使用 + 分隔表示 AND（两个关键词都必须存在）
    - 使用 | 分隔表示 OR（任一关键词存在即可）
    - 示例：
      - "blockchain+security" → title 包含 "blockchain" AND "security"
      - "security|iot"        → title 包含 "security" OR "iot"

    构建的 SQL 结构：
    1. 先在 title 中搜索：(title LIKE '%kw1%' AND/OR title LIKE '%kw2%')
    2. 再在 abstract 中搜索：(abstract LIKE '%kw1%' AND/OR abstract LIKE '%kw2%')
    3. 两者用 OR 连接
    4. 最后添加可选的 conference 和 year 筛选

    Args:
        q: 用户输入的搜索关键词字符串
        source: 会议筛选条件（如 "ccs,sp,uss"）
        year: 年份筛选条件（如 "2022,2023"）
        page: 未使用的参数

    Returns:
        SQL WHERE 子句字符串（不含 "WHERE" 关键字本身）

    示例返回：
        输入: q="ai+security", source="ccs", year="2022"
        返回: "(title LIKE '%ai%' AND title LIKE '%security%') OR (abstract LIKE '%ai%' AND abstract LIKE '%security%') AND conference IN (ccs) AND year IN (2022)"
    """
    tmp = []          # 临时存储字符
    keywords = []     # 存储解析出的关键词
    operator = []     # 存储运算符（and/or）

    # 对 source 和 year 进行"转义"处理
    source = sqlinjection(source)
    year = sqlinjection(year)

    # ========== 第一步：解析关键词和运算符 ==========
    i = 0
    finish_flag = False
    while i <= len(q):
        if i == len(q):
            # 到达字符串末尾，完成当前关键词
            finish_flag = True
        elif q[i] == "+":
            # 遇到 + ，表示 AND 运算
            operator.append("and")
            finish_flag = True
        elif q[i] == "|":
            # 遇到 | ，表示 OR 运算
            operator.append("or")
            finish_flag = True
        else:
            # 普通字符，添加到临时数组
            tmp.append(q[i])

        if finish_flag:
            # 将临时字符组合成关键词
            tmp_str = "".join(tmp).strip()
            if tmp_str:
                keywords.append(sqlinjection("".join(tmp).strip()))
            tmp = []           # 重置临时数组
            finish_flag = False
        i += 1

    # 验证：关键词数量应该比运算符多 1
    # 例如：3 个关键词需要 2 个运算符连接
    if len(keywords) - len(operator) != 1:
        print("Error")

    # ========== 第二步：构建 SQL WHERE 子句 ==========
    base_query = "("
    clause = ""

    # LIKE 查询模板
    base_title = "title LIKE '%{0}%'"
    base_abstract = "abstract LIKE '%{0}%'"

    # --- 构建 title 部分的查询条件 ---
    for i in range(len(operator)):
        try:
            clause += base_title.format(keywords[i])
            clause += " {0} ".format(operator[i])  # 添加 AND/OR
        except IndexError as e:
            print(e)
            # 出错时返回一个必定为空的条件
            return "SELECT * FROM papers WHERE year=1900"
    # 添加最后一个关键词（没有运算符跟随）
    clause += base_title.format(keywords[-1])

    # 用 OR 连接 abstract 部分
    clause += " OR "

    # --- 构建 abstract 部分的查询条件 ---
    for i in range(len(operator)):
        clause += base_abstract.format(keywords[i])
        clause += " {0} ".format(operator[i])
    clause += base_abstract.format(keywords[-1]) + ")"

    # ========== 第三步：添加可选的筛选条件 ==========
    if source is not None:
        # 会议筛选：conference IN (ccs, sp, uss, ...)
        clause += (" AND conference IN (" + source + ") ")
    if year is not None:
        # 年份筛选：year IN (2022, 2023, ...)
        clause += (" AND year IN (" + year + ") ")

    print(clause)
    return base_query + clause


# =============================================================================
# 路由：首页
# =============================================================================
@app.route('/')
def home():
    """返回首页（静态 HTML 文件）"""
    return app.send_static_file('index.html')


# =============================================================================
# 路由：搜索接口
# =============================================================================
@app.route('/search')
def get_info():
    """
    论文搜索 API

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
    q = request.args.get("q")
    source = request.args.get("s")
    year = request.args.get("y")
    offset = int(request.args.get("offset"))
    limit = int(request.args.get("limit"))

    # 连接数据库
    conn = sqlite3.connect(sys.path[0] + "/papers.db")
    c = conn.cursor()

    # 构建 WHERE 子句
    query = keywords(q, source, year, offset)
    results = []

    # ========== 查询总数 ==========
    try:
        base_q = "SELECT COUNT(*) FROM papers WHERE"
        cursor = c.execute(base_q + query)
        total = cursor.fetchone()[0]
    except sqlite3.Error as e:
        total = -1

    # ========== 查询实际数据 ==========
    try:
        query = "SELECT * FROM papers WHERE" + query
        query += " ORDER BY year DESC "
        query += "LIMIT {1} OFFSET {0}".format(offset, limit)

        cursor = c.execute(query)

        # 将查询结果转换为字典列表
        key_list = ["id", "conference", "year", "volume", "title",
                    "href", "origin", "abstract", "bib", "cat"]
        for item in cursor:
            results.append(dict(zip(key_list, item)))

        msg = {"code": 0, "msg": "success", "rows": results, "total": total}

    except sqlite3.OperationalError as e:
        msg = {"code": 1, "msg": str(e), "data": query}
    except sqlite3.IntegrityError as e:
        msg = {"code": 1, "msg": str(e), "data": query}
    finally:
        conn.close()

    return json.dumps(msg)


# =============================================================================
# 路由：获取论文摘要
# =============================================================================
@app.route('/abstract/<q>')
def get_abs(q):
    """
    获取指定论文的标题和摘要

    参数：
    - q: 论文 ID

    返回 JSON：
    {
        "code": 0,
        "msg": "success",
        "data": [[title, abstract]]
    }
    """
    conn = sqlite3.connect(sys.path[0] + "/papers.db")
    c = conn.cursor()

    # ⚠️ 注意：这里直接拼接 ID，虽然用 int() 转换了，但仍应使用参数化查询
    query = "SELECT title,abstract FROM papers WHERE id=" + str(int(q))
    results = []

    try:
        cursor = c.execute(query)
        for item in cursor:
            results.append(item)
        msg = {"code": 0, "msg": "success", "data": results}
    except sqlite3.OperationalError as e:
        msg = {"code": 1, "msg": str(e), "data": query}
    except sqlite3.IntegrityError as e:
        msg = {"code": 1, "msg": str(e), "data": query}
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
