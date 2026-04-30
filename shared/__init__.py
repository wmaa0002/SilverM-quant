"""
共享模块

提供信号系统和回测系统共用的数据接口和工具
"""

from .data import (
    BaseDataProvider,
    SignalDataAdapter,
    BacktestDataAdapter,
    IndicatorsCalculator,
)

__all__ = [
    'BaseDataProvider',
    'SignalDataAdapter',
    'BacktestDataAdapter',
    'IndicatorsCalculator',
]
