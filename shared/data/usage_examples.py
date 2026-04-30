"""
统一数据接口使用示例

展示如何在信号系统和回测系统中使用统一的数据接口
"""

from shared.data import SignalDataAdapter, BacktestDataAdapter, IndicatorsCalculator
import pandas as pd
import numpy as np


# ==================== 信号系统使用示例 ====================

def signal_system_example():
    """
    信号系统使用示例
    
    特点:
    - 直接从数据库获取数据
    - 计算 indicators 字典
    - 支持持仓信息查询
    """
    
    data_adapter = SignalDataAdapter()
    
    # 1. 获取股票数据
    code = '600000'
    trading_date = '2026-04-17'
    
    df = data_adapter.get_stock_data_by_trading_date(code, trading_date, days=150)
    
    if df is None:
        print(f"股票 {code} 数据不足")
        return
    
    # 2. 计算指标
    indicators = data_adapter.calculate_indicators(df, code)
    
    if indicators:
        print(f"股票 {code} 的指标:")
        print(f"  收盘价: {indicators['close']}")
        print(f"  涨幅: {indicators['涨幅']:.2f}%")
        print(f"  DIF: {indicators['dif']:.4f}")
        print(f"  KDJ: K={indicators['k']:.2f}, D={indicators['d']:.2f}, J={indicators['j']:.2f}")
        print(f"  知行短期趋势线: {indicators['知行短期趋势线']:.2f}")
        print(f"  知行多空线: {indicators['知行多空线']:.2f}")
    
    # 3. 获取持仓信息
    positions = data_adapter.get_positions()
    print(f"\n当前持仓数量: {len(positions)}")
    
    # 4. 获取持仓观察状态
    observation_state = data_adapter.get_positions_observation_state(code)
    if observation_state is not None:
        print(f"股票 {code} 观察状态: {'观察中' if observation_state else '无需观察'}")
    
    # 5. 更新观察状态
    data_adapter.update_positions_observation_state(code, True)


# ==================== 回测系统使用示例 ====================

def backtest_system_example():
    """
    回测系统使用示例
    
    特点:
    - 从数据库获取数据并转换为 backtrader 格式
    - 返回包含 datetime 索引的 DataFrame
    - 不需要持仓信息
    """
    
    data_adapter = BacktestDataAdapter()
    
    # 1. 获取股票数据
    code = '600000'
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    
    df = data_adapter.get_stock_data(code, start_date, end_date, min_days=60)
    
    if df is None:
        print(f"股票 {code} 数据不足")
        return
    
    # 2. 验证数据
    if data_adapter.validate_data_for_backtest(df):
        print(f"股票 {code} 数据验证通过")
        print(f"数据范围: {df.index[0]} 至 {df.index[-1]}")
        print(f"数据条数: {len(df)}")
    else:
        print(f"股票 {code} 数据验证失败")
        return
    
    # 3. 数据可以直接用于 backtrader
    print(f"\n数据格式:")
    print(df.head())


# ==================== 指标计算器独立使用示例 ====================

def indicators_calculator_example():
    """
    指标计算器独立使用示例
    
    可以在任何地方使用，不依赖数据适配器
    """
    
    # 构造示例数据
    data = {
        'date': pd.date_range('2024-01-01', periods=100),
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 105,
        'low': np.random.randn(100).cumsum() + 95,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randint(1000000, 10000000, 100)
    }
    df = pd.DataFrame(data)
    
    # 计算指标
    calc = IndicatorsCalculator()
    indicators = calc.calculate(df, '600000')
    
    if indicators:
        print("计算得到的指标:")
        print(f"  MA5: {indicators['ma5']:.2f}")
        print(f"  MA10: {indicators['ma10']:.2f}")
        print(f"  MA60: {indicators['ma60']:.2f}")
        print(f"  DIF: {indicators['dif']:.4f}")
        print(f"  KDJ: K={indicators['k']:.2f}, D={indicators['d']:.2f}, J={indicators['j']:.2f}")


# ==================== 迁移指南 ====================

def print_migration_guide():
    """
    打印迁移指南
    """
    print("=" * 60)
    print("迁移指南")
    print("=" * 60)
    
    print("\n1. 信号系统迁移:")
    print("   旧代码: 直接使用 duckdb 查询数据库")
    print("   新代码: 使用 SignalDataAdapter")
    print("   示例: data_adapter.get_stock_data_by_trading_date(code, date, days)")
    
    print("\n2. 回测系统迁移:")
    print("   旧代码: 直接使用 duckdb 查询数据库")
    print("   新代码: 使用 BacktestDataAdapter")
    print("   示例: data_adapter.get_stock_data(code, start, end, min_days)")
    
    print("\n3. 指标计算迁移:")
    print("   旧代码: from signals.singal_cal.basic_module import calculate_indicators")
    print("   新代码: from shared.data import IndicatorsCalculator")
    print("   示例: calc = IndicatorsCalculator(); indicators = calc.calculate(df, code)")
    
    print("\n" + "=" * 60)
    print("优势:")
    print("=" * 60)
    print("1. 统一接口: 信号系统和回测系统使用相同的数据获取方式")
    print("2. 代码复用: 指标计算逻辑只实现一次")
    print("3. 易于维护: 数据源变更只需修改适配器")
    print("4. 类型安全: 统一的返回格式")
    print("5. 易于测试: 可以轻松 mock 数据适配器")
    print("=" * 60)


if __name__ == '__main__':
    print("信号系统示例:")
    signal_system_example()
    
    print("\n" + "="*50 + "\n")
    
    print("回测系统示例:")
    backtest_system_example()
    
    print("\n" + "="*50 + "\n")
    
    print("指标计算器示例:")
    indicators_calculator_example()
    
    print("\n" + "="*50 + "\n")
    
    print_migration_guide()
