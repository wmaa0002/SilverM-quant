"""
统一数据接口模块

提供标准化的数据格式和接口，支持信号系统和回测系统
"""

from .base_data_provider import BaseDataProvider
from .signal_data_adapter import SignalDataAdapter
from .backtest_data_adapter import BacktestDataAdapter
from .indicators_calculator import IndicatorsCalculator

__all__ = [
    'BaseDataProvider',
    'SignalDataAdapter',
    'BacktestDataAdapter',
    'IndicatorsCalculator',
]
