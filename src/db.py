from enum import Enum
import mysql.connector

from config import DB_CONFIG

from enum import Enum
import mysql.connector
from config import DB_CONFIG  # 从配置文件导入数据库配置


class _QueryType(Enum):
    """ 用于定义查询结果类型的枚举 """
    NONE = 0  # 无结果
    ONE = 1   # 只获取一个结果 (findOne)
    ALL = 2   # 获取所有结果 (findAll)


pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="convert", pool_size=3, pool_reset_session=True, **DB_CONFIG)


def _execute(query, params=None, results=_QueryType.NONE):
    """
    执行带有参数的 SQL 查询，并根据指定的类型返回结果。

    :param query: 需要执行的 SQL 查询字符串。
    :param params: 查询的参数，通常是一个元组 (tuple)，默认为 None。
    :param results: 查询结果类型，使用 _QueryType 枚举来定义：
                    - _QueryType.NONE: 无结果（执行修改或删除操作）。
                    - _QueryType.ONE: 获取单个结果（fetchone）。
                    - _QueryType.ALL: 获取所有结果（fetchall）。
    :return: 根据结果类型返回查询结果：
             - _QueryType.ONE: 返回单个结果（元组或 None）。
             - _QueryType.ALL: 返回所有结果（元组列表或空列表）。
             - _QueryType.NONE: 返回 None（提交操作后不返回结果）。
    """
    try:
        # 使用提供的配置建立数据库连接
        conn = pool.get_connection()
        cursor = conn.cursor()

        # 执行查询并传递参数
        cursor.execute(query, params)

        # 根据 'results' 参数返回不同的查询结果
        if results is _QueryType.ONE:
            return cursor.fetchone()  # 获取单个结果
        if results is _QueryType.ALL:
            return cursor.fetchall()  # 获取所有结果
        conn.commit()  # 如果不需要结果，则提交事务

        return None  # 如果没有需要的结果，则返回 None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def db_execute(query, params=None):
    """
    执行带有参数的 SQL 查询，并且不期待结果。通常用于修改数据库的查询。

    :param query: 需要执行的 SQL 查询。
    :param params: SQL 查询的参数（通常是一个元组）。默认为 None。
    :return: None（执行并提交修改）。
    """
    # 执行查询，预期不返回结果（例如：INSERT、UPDATE、DELETE）
    return _execute(query, params, _QueryType.NONE)


def db_query_all(query, params=None):
    """
    执行 SQL 查询并预期获取所有结果。

    :param query: 需要执行的 SQL 查询。
    :param params: SQL 查询的参数（通常是一个元组）。默认为 None。
    :return: 返回所有查询结果（元组列表），如果没有结果，则返回空列表。
    """
    # 执行查询，预期获取所有结果（findAll）
    return _execute(query, params, _QueryType.ALL)


def db_query_one(query, params=None):
    """
    执行 SQL 查询并预期获取单个结果。

    :param query: 需要执行的 SQL 查询。
    :param params: SQL 查询的参数（通常是一个元组）。默认为 None。
    :return: 返回单个查询结果（元组），如果没有结果，则返回 None。
    """
    # 执行查询，预期获取单个结果（findOne）
    return _execute(query, params, _QueryType.ONE)


# def init_db():
#     try:
#         db_execute("""
#             CREATE TABLE IF NOT EXISTS report (
#                 reqid VARCHAR(255) PRIMARY KEY,
#                 jpgurl TEXT,
#                 totalpages INT,
#                 createtime DATETIME,
#                 lastupdate DATETIME
#             )
#         """)
#         db_execute("""
#             CREATE TABLE IF NOT EXISTS patient (
#                 recordid VARCHAR(255) PRIMARY KEY,
#                 reqid VARCHAR(255),
#                 FOREIGN KEY (reqid) REFERENCES report(reqid)
#             )
#         """)
#     except Exception as e:
#         print(f"数据库初始化失败: {str(e)}")
#         raise


# if __name__ == '__main__':
#     while (True):
#         a = db_query_all("""
#                 select r._id, p.recordid, p.anauploaddate, p.reviewuploaddate from patient p left join report r on p.reqid = r.reqid
#                 where
#                 (p.anauploaddate is not null and (r.imgupdate is null or p.anauploaddate > r.imgupdate) ) or
#                 (p.reviewuploaddate is not null and (r.imgupdate is null or p.reviewuploaddate  > r.imgupdate))
#                 limit 10
#             """)
#         print(a)
#         time.sleep(1)
#     # time.sleep(1000)
