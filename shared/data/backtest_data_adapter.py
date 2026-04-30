"""
回测系统数据适配器

为回测系统提供数据获取功能，兼容 backtrader 的数据格式
"""

from typing import Dict, Any, Optional, List
from datetime import date
import pandas as pd
import duckdb
from pathlib import Path

from .base_data_provider import BaseDataProvider


class BacktestDataAdapter(BaseDataProvider):
    """
    回测系统数据适配器
    
    特点:
    - 从数据库查询数据并转换为 backtrader 格式
    - 返回包含 datetime 索引的 DataFrame
    - 不需要持仓信息
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化回测数据适配器
        
        Args:
            db_path: 数据库路径，默认使用 Astock3.duckdb
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / 'data' / 'Astock3.duckdb'
        
        self.db_path = str(db_path)
    
    def _get_connection(self):
        """获取数据库连接（只读）"""
        return duckdb.connect(self.db_path, read_only=True)
    
    def get_stock_data(
        self,
        code: str,
        start_date: str,
        end_date: str,
        min_days: int = 60
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据（backtrader 格式）
        
        Args:
            code: 股票代码（6位数字格式）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            min_days: 最少数据天数
        
        Returns:
            DataFrame 包含:
            - datetime: 日期索引
            - open, high, low, close, volume: OHLCV 数据
        """
        conn = self._get_connection()
        try:
            ts_code = self.code_to_ts_code(code)
            
            df = conn.execute("""
                SELECT 
                    trade_date,
                    open,
                    high,
                    low,
                    close,
                    vol as volume,
                    amount as openinterest
                FROM dwd_daily_price
                WHERE ts_code = ?
                AND trade_date >= ?
                AND trade_date <= ?
                ORDER BY trade_date
            """, [ts_code, start_date, end_date]).fetchdf()
            
            if df is None or len(df) == 0:
                return None
            
            if len(df) < min_days:
                return None
            
            df = df.rename(columns={'trade_date': 'datetime'})
            df['datetime'] = pd.to_datetime(df['datetime'])
            df = df.set_index('datetime')
            
            return df
        finally:
            conn.close()
    
    def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息
        
        Args:
            code: 股票代码
        
        Returns:
            包含 code, name, industry, list_date 的字典
        """
        conn = self._get_connection()
        try:
            ts_code = self.code_to_ts_code(code)
            
            result = conn.execute("""
                SELECT 
                    symbol as code,
                    name,
                    industry,
                    list_date
                FROM dwd_stock_info
                WHERE ts_code = ?
                AND list_status = 'L'
            """, [ts_code]).fetchone()
            
            if result is None:
                return None
            
            return {
                'code': result[0],
                'name': result[1],
                'industry': result[2],
                'list_date': str(result[3]) if result[3] else None
            }
        finally:
            conn.close()
    
    def get_stock_list(
        self,
        industry: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取股票列表
        
        Args:
            industry: 行业过滤
            limit: 数量限制
        
        Returns:
            股票列表
        """
        conn = self._get_connection()
        try:
            query = """
                SELECT 
                    symbol as code,
                    name,
                    industry
                FROM dwd_stock_info
                WHERE list_status = 'L'
            """
            
            params = []
            if industry:
                query += " AND industry = ?"
                params.append(industry)
            
            query += " ORDER BY symbol"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            df = conn.execute(query, params).fetchdf()
            
            return df.to_dict('records')
        finally:
            conn.close()
    
    def get_positions(self) -> pd.DataFrame:
        """
        回测系统不需要持仓信息
        
        Returns:
            空 DataFrame
        """
        return pd.DataFrame()
    
    def get_data_for_backtest(
        self,
        code: str,
        start_date: str,
        end_date: str,
        min_days: int = 60
    ) -> Optional[pd.DataFrame]:
        """
        获取回测专用数据格式
        
        Args:
            code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            min_days: 最少数据天数
        
        Returns:
            DataFrame 包含 datetime 索引和 OHLCV 数据
        """
        return self.get_stock_data(code, start_date, end_date, min_days)
    
    def get_data_for_backtrader(
        self,
        code: str,
        fromdate: Optional[date] = None,
        todate: Optional[date] = None,
        min_days: int = 60
    ) -> Optional[pd.DataFrame]:
        """
        获取 backtrader 专用数据格式
        
        Args:
            code: 股票代码
            fromdate: 开始日期 (date 对象)
            todate: 结束日期 (date 对象)
            min_days: 最少数据天数
        
        Returns:
            DataFrame 包含 datetime 索引和 OHLCV 数据
        """
        start_date = fromdate.strftime('%Y-%m-%d') if fromdate else None
        end_date = todate.strftime('%Y-%m-%d') if todate else None
        
        return self.get_stock_data(code, start_date, end_date, min_days)
    
    def validate_data_for_backtest(self, df: pd.DataFrame) -> bool:
        """
        验证数据是否适合回测
        
        Args:
            df: 数据 DataFrame
        
        Returns:
            是否适合回测
        """
        if df is None or len(df) == 0:
            return False
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                return False
        
        if df.isnull().any().any():
            return False
        
        return True
