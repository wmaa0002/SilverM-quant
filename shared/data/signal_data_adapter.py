"""
信号系统数据适配器

为信号系统提供数据获取和指标计算功能
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import duckdb
from pathlib import Path

from .base_data_provider import BaseDataProvider
from .indicators_calculator import IndicatorsCalculator


class SignalDataAdapter(BaseDataProvider):
    """
    信号系统数据适配器
    
    特点:
    - 直接从数据库查询数据
    - 计算并返回 indicators 字典
    - 支持持仓信息查询
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化信号数据适配器
        
        Args:
            db_path: 数据库路径，默认使用 Astock3.duckdb
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / 'data' / 'Astock3.duckdb'
        
        self.db_path = str(db_path)
        self.indicator_calc = IndicatorsCalculator()
    
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
        获取股票历史数据
        
        Args:
            code: 股票代码（6位数字格式）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            min_days: 最少数据天数
        
        Returns:
            DataFrame 包含 date, open, high, low, close, volume
        """
        conn = self._get_connection()
        try:
            ts_code = self.code_to_ts_code(code)
            
            df = conn.execute("""
                SELECT 
                    trade_date as date,
                    open,
                    high,
                    low,
                    close,
                    vol as volume
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
            
            return df
        finally:
            conn.close()
    
    def get_stock_data_by_trading_date(
        self,
        code: str,
        trading_date: str,
        days: int = 150
    ) -> Optional[pd.DataFrame]:
        """
        获取指定交易日期之前的历史数据（用于信号扫描）
        
        Args:
            code: 股票代码
            trading_date: 交易日期 (YYYY-MM-DD)
            days: 获取天数
        
        Returns:
            DataFrame
        """
        conn = self._get_connection()
        try:
            ts_code = self.code_to_ts_code(code)
            
            df = conn.execute("""
                SELECT 
                    trade_date as date,
                    open,
                    high,
                    low,
                    close,
                    vol as volume
                FROM dwd_daily_price
                WHERE ts_code = ?
                AND trade_date <= ?
                ORDER BY trade_date DESC
                LIMIT ?
            """, [ts_code, trading_date, days]).fetchdf()
            
            if df is None or len(df) == 0:
                return None
            
            if len(df) < 60:
                return None
            
            df = df.sort_values('date').reset_index(drop=True)
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
        获取当前持仓信息
        
        Returns:
            DataFrame 包含持仓信息
        """
        conn = self._get_connection()
        try:
            df = conn.execute("""
                SELECT 
                    code,
                    strategy,
                    buy_price,
                    status,
                    buy_date,
                    current_跌破多空线
                FROM positions
                WHERE status = 'holding'
                ORDER BY buy_date DESC
            """).fetchdf()
            
            return df
        finally:
            conn.close()
    
    def get_positions_observation_state(self, code: str) -> Optional[bool]:
        """
        获取持仓股票的观察状态
        
        Args:
            code: 股票代码
        
        Returns:
            True: 处于观察期
            False: 观察期已结束或无需观察
            None: 不在持仓中
        """
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT current_跌破多空线
                FROM positions
                WHERE code = ? AND status = 'holding'
            """, [code]).fetchone()
            
            if result is None:
                return None
            
            val = result[0]
            if val is None or pd.isna(val):
                return False
            return bool(val)
        finally:
            conn.close()
    
    def update_positions_observation_state(self, code: str, is_observing: bool):
        """
        更新持仓股票的观察状态
        
        Args:
            code: 股票代码
            is_observing: 是否处于观察期
        """
        conn = duckdb.connect(self.db_path, read_only=False)
        try:
            conn.execute("""
                UPDATE positions
                SET current_跌破多空线 = ?
                WHERE code = ? AND status = 'holding'
            """, [is_observing, code])
        finally:
            conn.close()
    
    def calculate_indicators(
        self,
        df: pd.DataFrame,
        code: str
    ) -> Optional[Dict[str, Any]]:
        """
        计算技术指标
        
        Args:
            df: 股票历史数据
            code: 股票代码
        
        Returns:
            包含所有指标的字典
        """
        if df is None or len(df) < 60:
            return None
        
        return self.indicator_calc.calculate(df, code)
    
    def get_latest_trading_date(self) -> Optional[str]:
        """
        获取最新交易日期
        
        Returns:
            最新交易日期 (YYYY-MM-DD)
        """
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT MAX(trade_date)
                FROM dwd_daily_price
            """).fetchone()
            
            return str(result[0]) if result[0] else None
        finally:
            conn.close()
