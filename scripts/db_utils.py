"""数据库连接工具模块"""

import os
import duckdb
from contextlib import contextmanager
from datetime import date

# 数据库路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'Astock3.duckdb')


@contextmanager
def get_db_connection(read_only: bool = True):
    """
    获取数据库连接的上下文管理器

    Args:
        read_only: 是否以只读模式打开连接

    Yields:
        duckdb.DuckDBPyConnection: 数据库连接
    """
    conn = duckdb.connect(DB_PATH, read_only=read_only)
    try:
        yield conn
    finally:
        conn.close()


def is_trading_day_tushare(check_date: date = None) -> bool:
    """
    使用 tushare trade_cal 接口判断是否为交易日

    Args:
        check_date: 待检查日期，默认为今天

    Returns:
        bool: 是否为交易日
    """
    if check_date is None:
        check_date = date.today()

    try:
        import tushare as ts
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            # 没有token，回退到数据库检查
            return _is_trading_day_by_db(check_date)

        pro = ts.pro_api(token)
        df = pro.trade_cal(
            exchange='SSE',
            start_date=check_date.strftime('%Y%m%d'),
            end_date=check_date.strftime('%Y%m%d')
        )
        if df is None or df.empty:
            return False
        # is_open=1 表示交易日
        return int(df.iloc[0]['is_open']) == 1
    except Exception:
        # 接口失败，回退到数据库检查
        return _is_trading_day_by_db(check_date)


def _is_trading_day_by_db(check_date: date) -> bool:
    """通过数据库中是否有价格数据判断是否为交易日（回退方案）"""
    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        result = conn.execute(
            "SELECT COUNT(*) FROM dwd_daily_price WHERE trade_date = ?",
            [check_date.strftime('%Y-%m-%d')]
        ).fetchone()
        return result is not None and result[0] > 0
    finally:
        conn.close()
