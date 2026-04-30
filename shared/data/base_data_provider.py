"""
数据提供者基类

定义统一的数据接口规范
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np


class BaseDataProvider(ABC):
    """
    数据提供者基类
    
    定义统一的数据获取接口，支持不同数据源和场景
    """
    
    @abstractmethod
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
            code: 股票代码（统一使用 6位数字格式，如 '600000'）
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            min_days: 最少数据天数
        
        Returns:
            DataFrame 包含以下列:
            - date: 交易日期
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - close: 收盘价
            - volume: 成交量
        """
        pass
    
    @abstractmethod
    def get_stock_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息
        
        Args:
            code: 股票代码
        
        Returns:
            包含股票信息的字典:
            - code: 股票代码
            - name: 股票名称
            - industry: 行业
            - list_date: 上市日期
        """
        pass
    
    @abstractmethod
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
            股票列表，每个元素包含 code, name, industry
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> pd.DataFrame:
        """
        获取当前持仓信息（仅信号系统需要）
        
        Returns:
            DataFrame 包含持仓信息
        """
        pass
    
    def code_to_ts_code(self, code: str) -> str:
        """
        转换股票代码为 tushare 格式
        
        Args:
            code: 6位数字代码
        
        Returns:
            ts_code 格式 (如 '600000.SH', '000001.SZ')
        """
        code = str(code)
        if code.startswith('6'):
            return f"{code}.SH"
        else:
            return f"{code}.SZ"
    
    def ts_code_to_code(self, ts_code: str) -> str:
        """
        转换 tushare 格式为 6位数字代码
        
        Args:
            ts_code: tushare 格式 (如 '600000.SH', '000001.SZ')
        
        Returns:
            6位数字代码
        """
        return ts_code.split('.')[0]
