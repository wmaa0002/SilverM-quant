"""
投资组合回测脚本 - True Portfolio Simulation

使用单个Cerebro实例管理整个投资组合，所有股票同时加载到Cerebro。
策略的next()方法由Cerebro自动驱动，每个交易日会遍历所有股票。
Broker统一管理账户现金和持仓，输出组合层面的绩效指标。

Key patterns:
- cereb = bt.Cerebro()
- cereb.broker.setcash(initial_cash)
- cereb.broker.setcommission(commission=0.0003)
- for data in self.datas:  # walk all stocks in next()
- self.daily_values.append(self.broker.getvalue())
- Calculate metrics from daily_values array

使用示例:
    python batch_backtest_portfolio.py -l 50 --start 20250101 --end 20251231
"""

import sys
import argparse
import os
import logging
import warnings
import json
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import inspect

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
import duckdb
import backtrader as bt

from strategies.registry import Registry
from scripts.log_utils import setup_logger

# Registry单例
registry = Registry()

ASTOCK3_DB_PATH = project_root / 'data' / 'Astock3.duckdb'


def add_exchange_suffix(code: str) -> str:
    """根据股票代码前缀判断交易所后缀

    规则:
    - 688xxx, 600xxx, 601xxx, 603xxx, 605xxx -> .SH (上证)
    - 000xxx, 001xxx, 002xxx, 003xxx, 300xxx -> .SZ (深证)
    - 920xxx -> .BJ (北交所)
    """
    if code.startswith(('688', '600', '601', '603', '605')):
        return f"{code}.SH"
    elif code.startswith(('000', '001', '002', '003', '300')):
        return f"{code}.SZ"
    elif code.startswith('920'):
        return f"{code}.BJ"
    else:
        return code


def get_data_from_astock3(stock_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """获取单个股票数据"""
    start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    end_date_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

    ts_code = add_exchange_suffix(stock_code)

    conn = duckdb.connect(str(ASTOCK3_DB_PATH))
    df = conn.execute(f"""
        SELECT trade_date, ts_code, open, high, low, close, vol, amount
        FROM dwd_daily_price
        WHERE ts_code = '{ts_code}'
        AND trade_date >= '{start_date_fmt}'
        AND trade_date <= '{end_date_fmt}'
        ORDER BY trade_date
    """).fetchdf()
    conn.close()

    if df is None or len(df) == 0:
        return None

    df = df.rename(columns={
        'trade_date': 'date',
        'ts_code': 'code',
        'vol': 'volume'
    })

    # 转换日期格式
    df['date'] = pd.to_datetime(df['date'])
    df = df.rename(columns={
        'date': 'datetime',
        'amount': 'openinterest'
    })

    return df


def get_stock_list_from_db(limit: int = None, industry: str = None) -> pd.DataFrame:
    """从数据库获取股票列表"""
    conn = duckdb.connect(str(ASTOCK3_DB_PATH))

    query = "SELECT symbol AS code, name, industry FROM dwd_stock_info WHERE list_status = 'L'"

    if industry:
        query += f" AND industry = '{industry}'"

    if limit:
        query += f" LIMIT {limit}"

    df = conn.execute(query).df()
    conn.close()
    return df


def load_strategy_class(strategy_name: str):
    """加载策略类"""
    strategy_class = registry.get(strategy_name)
    if strategy_class is not None:
        return strategy_class

    # 回退到旧方法
    warnings.warn(
        f"策略 '{strategy_name}' 未在注册表中，使用 exec() 加载已废弃。",
        DeprecationWarning,
        stacklevel=2
    )
    strategy_file = project_root / 'strategies' / f'{strategy_name}.py'

    with open(strategy_file, 'r', encoding='utf-8') as f:
        content = f.read()

    namespace = {}
    exec(content, namespace)

    for name in namespace:
        if name.endswith('Strategy') and name != 'BaseStrategy':
            return namespace[name]

    raise ValueError(f"未找到策略类 in {strategy_file}")


def get_strategy_config(strategy_file: str) -> dict:
    """获取策略配置"""
    metadata = registry.get_metadata(strategy_file)

    if metadata is not None:
        return {
            'threshold_required': metadata.threshold_required,
            'min_data_days': metadata.min_data_days,
        }
    else:
        logging.warning(f"策略 '{strategy_file}' 未在注册表中，使用默认配置")
        return {
            'threshold_required': True,
            'min_data_days': 60,
        }


class PortfolioStrategy(bt.Strategy):
    """
    投资组合策略基类

    在next()中遍历所有股票数据进行策略判断。
    使用self.datas访问所有数据，self.broker.getvalue()获取组合总值。
    """

    params = (
        ('threshold', 8.0),
        ('stop_loss_pct', 0.05),
        ('min_data_points', 60),
        ('max_positions', 10),  # 最大持仓数量
        ('debug_mode', False),
    )

    节假日列表 = [
        datetime(2024, 2, 12), datetime(2024, 2, 13), datetime(2024, 2, 14),
        datetime(2024, 4, 4), datetime(2024, 4, 5), datetime(2024, 5, 1),
        datetime(2024, 5, 2), datetime(2024, 5, 3), datetime(2024, 6, 10),
        datetime(2024, 9, 16), datetime(2024, 9, 17), datetime(2024, 10, 1),
        datetime(2024, 10, 2), datetime(2024, 10, 3), datetime(2024, 10, 4),
        datetime(2024, 10, 7), datetime(2025, 1, 28), datetime(2025, 1, 29),
        datetime(2025, 1, 30), datetime(2025, 1, 31), datetime(2025, 4, 4),
        datetime(2025, 5, 1), datetime(2025, 5, 2), datetime(2025, 6, 2),
        datetime(2025, 10, 1), datetime(2025, 10, 2), datetime(2025, 10, 3),
        datetime(2025, 10, 6), datetime(2025, 10, 7), datetime(2025, 10, 8),
        datetime(2026, 1, 1), datetime(2026, 1, 2), datetime(2026, 1, 3),
        datetime(2026, 2, 15), datetime(2026, 2, 16), datetime(2026, 2, 17),
        datetime(2026, 2, 18), datetime(2026, 2, 19), datetime(2026, 2, 20),
        datetime(2026, 2, 21), datetime(2026, 2, 22), datetime(2026, 2, 23),
        datetime(2026, 4, 4), datetime(2026, 4, 5), datetime(2026, 4, 6),
        datetime(2026, 5, 1), datetime(2026, 5, 2), datetime(2026, 5, 3),
        datetime(2026, 5, 4), datetime(2026, 5, 5), datetime(2026, 6, 19),
        datetime(2026, 6, 20), datetime(2026, 6, 21), datetime(2026, 9, 25),
        datetime(2026, 9, 26), datetime(2026, 9, 27), datetime(2026, 10, 1),
        datetime(2026, 10, 2), datetime(2026, 10, 3), datetime(2026, 10, 4),
        datetime(2026, 10, 5), datetime(2026, 10, 6), datetime(2026, 10, 7)
    ]

    def __init__(self):
        self.daily_values = []  # 每日组合价值
        self.daily_dates = []  # 每日日期
        self.trade_records = []  # 交易记录
        self.pending_orders = {}  # 待处理订单 {data._name: order}

    def log(self, txt, dt=None):
        """日志"""
        if self.params.debug_mode:
            dt = dt or self.datas[0].datetime.datetime(0)
            print(f'{dt.isoformat()} - {txt}')

    def prenext(self):
        """数据不足时的回调"""
        self.next()

    def next(self):
        """
        每个交易日被Cerebro自动调用
        遍历所有股票数据进行策略判断
        """
        # 记录每日组合价值
        current_date = self.datas[0].datetime.datetime(0)
        portfolio_value = self.broker.getvalue()
        self.daily_values.append(portfolio_value)
        self.daily_dates.append(current_date)

        # 跳过预热期
        if len(self) < self.params.min_data_points:
            return

        # 时间过滤 - 14:30尾盘
        if current_date.hour == 14 and current_date.minute >= 30:
            return

        # 节假日过滤
        for holiday in self.节假日列表:
            if current_date.date() == holiday.date():
                return

        # 遍历所有股票
        for data in self.datas:
            self._process_stock(data)

    def _process_stock(self, data):
        """处理单个股票"""
        data_name = data._name

        # 检查是否有待处理订单
        if data_name in self.pending_orders:
            return  # 等待订单完成

        # 获取持仓
        position = self.getposition(data)

        if not position:
            # 无持仓，检查是否买入
            if self._should_buy(data):
                self._execute_buy(data)
        else:
            # 有持仓，检查是否卖出
            if self._should_sell(data, position):
                self._execute_sell(data)

    def _should_buy(self, data) -> bool:
        """判断是否应该买入 - 子类可重写"""
        return False

    def _should_sell(self, data, position) -> bool:
        """判断是否应该卖出 - 子类可重写"""
        return False

    def _execute_buy(self, data):
        """执行买入"""
        # 检查是否超过最大持仓数
        current_positions = len([d for d in self.datas if self.getposition(d).size > 0])
        if current_positions >= self.params.max_positions:
            return

        price = data.close[0]
        cash = self.broker.getcash()
        available_cash = cash * 0.95  # 预留5%现金

        if available_cash < price * 100:
            return

        size = int(available_cash / price / 100) * 100
        if size < 100:
            return

        self.log(f'BUY {data._name} {size} @ {price:.2f}')
        order = self.buy(data=data, size=size)
        self.pending_orders[data._name] = order

    def _execute_sell(self, data):
        """执行卖出"""
        self.log(f'SELL {data._name}')
        order = self.close(data=data)
        self.pending_orders[data._name] = order

    def notify_order(self, order):
        """订单通知"""
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            data_name = order.data._name if hasattr(order.data, '_name') else order.data._name
            if data_name in self.pending_orders:
                del self.pending_orders[data_name]

            if order.status == order.Completed:
                current_date = self.datas[0].datetime.datetime(0)
                if order.isbuy():
                    self.trade_records.append({
                        'date': current_date,
                        'action': 'BUY',
                        'code': data_name,
                        'price': order.executed.price,
                        'size': order.executed.size,
                    })
                else:
                    self.trade_records.append({
                        'date': current_date,
                        'action': 'SELL',
                        'code': data_name,
                        'price': order.executed.price,
                        'size': order.executed.size,
                    })

    def get_daily_values(self) -> List[float]:
        """获取每日组合价值"""
        return self.daily_values

    def get_daily_dates(self) -> List[datetime]:
        """获取每日日期"""
        return self.daily_dates


class SimpleBuyAndHoldPortfolio(PortfolioStrategy):
    """
    简单的买入持有策略 - 用于基准对比
    """

    def __init__(self):
        super().__init__()
        self.initialized = False

    def next(self):
        """每个股票只买入一次，之后持有"""
        # 记录每日价值
        current_date = self.datas[0].datetime.datetime(0)
        portfolio_value = self.broker.getvalue()
        self.daily_values.append(portfolio_value)
        self.daily_dates.append(current_date)

        # 跳过预热期
        if len(self) < self.params.min_data_points:
            return

        # 时间过滤
        if current_date.hour == 14 and current_date.minute >= 30:
            return

        # 节假日过滤
        for holiday in self.节假日列表:
            if current_date.date() == holiday.date():
                return

        # 每个股票只买入一次
        for data in self.datas:
            position = self.getposition(data)
            if not position:
                # 检查是否超过最大持仓
                current_positions = len([d for d in self.datas if self.getposition(d).size > 0])
                if current_positions >= self.params.max_positions:
                    continue

                price = data.close[0]
                cash = self.broker.getcash()
                available_cash = cash * 0.95

                if available_cash < price * 100:
                    continue

                size = int(available_cash / price / 100) * 100
                if size >= 100:
                    self.log(f'BUY {data._name} {size} @ {price:.2f}')
                    self.buy(data=data, size=size)


def calculate_metrics(daily_values: List[float], initial_cash: float) -> Dict[str, Any]:
    """
    从每日组合价值计算绩效指标

    Args:
        daily_values: 每日组合价值列表
        initial_cash: 初始资金

    Returns:
        绩效指标字典
    """
    if not daily_values:
        return {}

    values = np.array(daily_values, dtype=float)
    valid_mask = np.isfinite(values)
    values = values[valid_mask]

    if len(values) == 0:
        return {}

    final_value = values[-1]
    total_return = (final_value - initial_cash) / initial_cash

    num_days = len(values)
    years = num_days / 252
    annualized_return = (final_value / initial_cash) ** (1 / years) - 1 if years > 0 else 0

    peak = values[0]
    max_drawdown = 0
    max_drawdown_duration = 0
    current_drawdown_duration = 0

    for value in values:
        if value > peak:
            peak = value
            current_drawdown_duration = 0
        else:
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            current_drawdown_duration += 1
            if current_drawdown_duration > max_drawdown_duration:
                max_drawdown_duration = current_drawdown_duration

    daily_returns = np.diff(values) / values[:-1]
    daily_returns = daily_returns[np.isfinite(daily_returns)]
    volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 1 else 0

    risk_free_rate = 0.03
    excess_return = annualized_return - risk_free_rate
    sharpe_ratio = excess_return / volatility if volatility > 0 else 0

    negative_returns = daily_returns[daily_returns < 0]
    downside_volatility = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 1 else 0.01
    sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0

    calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0

    return {
        'initial_cash': initial_cash,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'max_drawdown': max_drawdown,
        'max_drawdown_duration': max_drawdown_duration,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'calmar_ratio': calmar_ratio,
        'num_days': num_days,
        'daily_values': values.tolist(),
    }


def run_portfolio_backtest(
    stocks: List[Dict],
    start_date: str,
    end_date: str,
    strategy_class,
    initial_cash: float = 1000000.0,
    commission: float = 0.0003,
    threshold: float = 8.0,
    max_positions: int = 10,
    save_to_db: bool = True,
    strategy_params: Dict = None
) -> Dict[str, Any]:
    """
    运行投资组合回测

    使用单个Cerebro实例，所有股票同时加载。
    Broker统一管理现金和持仓。
    """
    import backtrader as bt

    # 解析日期
    from_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    to_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"

    # 创建Cerebro
    cereb = bt.Cerebro()

    # 设置初始资金
    cereb.broker.setcash(initial_cash)

    # 设置手续费
    cereb.broker.setcommission(commission=commission)

    # 添加策略
    strategy_params = strategy_params or {}
    cereb.addstrategy(
        strategy_class,
        threshold=threshold,
        max_positions=max_positions,
        **strategy_params
    )

    # 添加数据
    data_map = {}  # code -> data
    valid_stocks = []

    for stock in stocks:
        code = stock.get('code', '')
        name = stock.get('name', '')

        df = get_data_from_astock3(code, start_date, end_date)

        if df is None or len(df) < 60:
            continue

        # 清理NaN/NaT值 - backtrader不能处理缺失值
        # 删除datetime为NaT的行
        df = df[df['datetime'].notna()]
        # 删除数值列的NaN值（用前值填充）
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].ffill().fillna(0)
        # 删除仍然有NaN的行
        df = df.dropna()

        if len(df) < 60:
            continue

        # 转换日期格式
        bt_fromdate = datetime.strptime(from_date, '%Y-%m-%d').date()
        bt_todate = datetime.strptime(to_date, '%Y-%m-%d').date()

        # 设置datetime为索引（backtrader要求datetime作为索引）
        df = df.set_index('datetime')

        data = bt.feeds.PandasData(
            dataname=df,
            name=code,
            fromdate=bt_fromdate,
            todate=bt_todate
        )

        cereb.adddata(data, name=code)
        data_map[code] = df
        valid_stocks.append({'code': code, 'name': name, 'data_len': len(df)})

    if not valid_stocks:
        return {
            'status': 'no_data',
            'error': '没有有效股票数据'
        }

    # 添加分析器
    cereb.addanalyzer(bt.analyzers.Returns, _name='returns')
    cereb.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cereb.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cereb.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    # 运行回测
    results = cereb.run()
    strat = results[0]

    # 获取每日价值
    daily_values = strat.get_daily_values()
    daily_dates = strat.get_daily_dates()

    # 计算指标
    metrics = calculate_metrics(daily_values, initial_cash)

    # 获取交易统计
    trades_analyzer = strat.analyzers.trades.get_analysis()

    total_trades = 0
    won_trades = 0
    lost_trades = 0

    if trades_analyzer:
        total_trades = trades_analyzer.get('total', {}).get('total', 0)
        won_trades = trades_analyzer.get('won', {}).get('total', 0)
        lost_trades = trades_analyzer.get('lost', {}).get('total', 0)

    metrics['total_trades'] = total_trades
    metrics['winning_trades'] = won_trades
    metrics['losing_trades'] = lost_trades
    metrics['win_rate'] = won_trades / total_trades if total_trades > 0 else 0

    # 清理交易记录中的datetime对象，转换为ISO格式字符串
    cleaned_trade_records = []
    for record in strat.trade_records:
        cleaned_record = {}
        for k, v in record.items():
            if hasattr(v, 'isoformat'):  # datetime对象
                cleaned_record[k] = v.isoformat()
            elif isinstance(v, (np.integer, np.floating)):  # numpy数值类型
                cleaned_record[k] = float(v) if isinstance(v, np.floating) else int(v)
            else:
                cleaned_record[k] = v
        cleaned_trade_records.append(cleaned_record)

    # 清理每日values中的numpy类型
    cleaned_daily_values = [float(v) if isinstance(v, (np.integer, np.floating)) else v for v in daily_values]

    # 构建结果
    result = {
        'status': 'success',
        'initial_cash': float(initial_cash),
        'final_value': float(metrics['final_value']),
        'total_return': float(metrics['total_return']),
        'annualized_return': float(metrics['annualized_return']),
        'max_drawdown': float(metrics['max_drawdown']),
        'max_drawdown_duration': int(metrics['max_drawdown_duration']),
        'sharpe_ratio': float(metrics['sharpe_ratio']),
        'sortino_ratio': float(metrics['sortino_ratio']),
        'calmar_ratio': float(metrics['calmar_ratio']),
        'volatility': float(metrics['volatility']),
        'total_trades': int(total_trades),
        'winning_trades': int(won_trades),
        'losing_trades': int(lost_trades),
        'win_rate': float(metrics['win_rate']),
        'num_days': int(metrics['num_days']),
        'valid_stocks': int(len(valid_stocks)),
        'trade_records': cleaned_trade_records,
        'daily_values': cleaned_daily_values,
        'daily_dates': [d.isoformat() for d in daily_dates],
        'equity_curve': [(d.isoformat() if hasattr(d, 'isoformat') else d, float(v) if isinstance(v, (np.integer, np.floating)) else v) for d, v in zip(daily_dates, daily_values)],
    }

    return result


def print_portfolio_results(result: Dict[str, Any]):
    """打印投资组合回测结果"""
    print("\n" + "=" * 60)
    print("投资组合回测结果")
    print("=" * 60)
    print(f"初始资金:      {result['initial_cash']:>15,.2f}")
    print(f"最终价值:      {result['final_value']:>15,.2f}")
    print(f"总收益率:      {result['total_return']*100:>15.2f}%")
    print(f"年化收益率:    {result['annualized_return']*100:>15.2f}%")
    print("-" * 60)
    print(f"夏普比率:      {result['sharpe_ratio']:>15.2f}")
    print(f"索提比率:      {result['sortino_ratio']:>15.2f}")
    print(f"卡玛比率:      {result['calmar_ratio']:>15.2f}")
    print(f"波动率:        {result['volatility']*100:>15.2f}%")
    print(f"最大回撤:      {result['max_drawdown']*100:>15.2f}%")
    print(f"最大回撤天数:  {result['max_drawdown_duration']:>15}")
    print("-" * 60)
    print(f"总交易次数:    {result['total_trades']:>15}")
    print(f"盈利交易:      {result['winning_trades']:>15}")
    print(f"亏损交易:      {result['losing_trades']:>15}")
    print(f"胜率:          {result['win_rate']*100:>15.2f}%")
    print("-" * 60)
    print(f"有效股票数:    {result['valid_stocks']:>15}")
    print(f"回测天数:      {result['num_days']:>15}")
    print("=" * 60)


def save_results_to_csv(result: Dict[str, Any], output_path: str):
    """保存结果到CSV"""
    # 保存权益曲线
    equity_df = pd.DataFrame(result['equity_curve'], columns=['date', 'value'])
    equity_path = output_path.replace('.csv', '_equity.csv')
    equity_df.to_csv(equity_path, index=False)
    print(f"权益曲线已保存到: {equity_path}")

    # 保存交易记录
    if result.get('trade_records'):
        trades_df = pd.DataFrame(result['trade_records'])
        trades_path = output_path.replace('.csv', '_trades.csv')
        trades_df.to_csv(trades_path, index=False, encoding='utf-8-sig')
        print(f"交易记录已保存到: {trades_path}")


def main():
    parser = argparse.ArgumentParser(description='投资组合回测 - True Portfolio Simulation')

    parser.add_argument('--stocks', '-s', nargs='+', default=None,
                       help='股票代码列表')
    parser.add_argument('--stock-file', '-f', default=None,
                       help='股票代码文件')
    parser.add_argument('--limit', '-l', type=int, default=None,
                       help='从数据库获取的股票数量')
    parser.add_argument('--industry', '-i', type=str, default=None,
                       help='行业过滤')
    parser.add_argument('--start', default='20250101', help='开始日期 YYYYMMDD')
    parser.add_argument('--end', default='20251231', help='结束日期 YYYYMMDD')
    parser.add_argument('--cash', type=float, default=1000000, help='初始资金')
    parser.add_argument('--strategy', default='天宫B1策略v1', help='策略文件名')
    parser.add_argument('--threshold', type=float, default=8.0, help='策略阈值')
    parser.add_argument('--max-positions', type=int, default=10, help='最大持仓数')
    parser.add_argument('--no-save', action='store_true', help='不保存到CSV')
    parser.add_argument('--output', '-o', default=None, help='结果输出路径')
    parser.add_argument('--benchmark', action='store_true', help='同时运行基准测试(买入持有)')

    args = parser.parse_args()

    # 获取股票列表
    stocks = None

    if args.stocks:
        stocks = [{'code': code, 'name': ''} for code in args.stocks]
    elif args.stock_file:
        with open(args.stock_file, 'r') as f:
            codes = [line.strip() for line in f if line.strip()]
        stocks = [{'code': code, 'name': ''} for code in codes]
    elif args.limit or args.industry:
        stock_df = get_stock_list_from_db(limit=args.limit, industry=args.industry)
        stocks = stock_df.to_dict('records')
    else:
        # 默认从数据库获取50只
        stock_df = get_stock_list_from_db(limit=50)
        stocks = stock_df.to_dict('records')

    print(f"股票数量: {len(stocks)}")
    print(f"回测期间: {args.start} - {args.end}")
    print(f"初始资金: {args.cash:,.0f}")
    print(f"策略: {args.strategy}")

    # 加载策略
    try:
        strategy_class = load_strategy_class(args.strategy)
    except Exception as e:
        print(f"加载策略失败: {e}")
        # 使用默认策略
        strategy_class = SimpleBuyAndHoldPortfolio
        print("使用默认策略: SimpleBuyAndHoldPortfolio")

    # 运行投资组合回测
    result = run_portfolio_backtest(
        stocks=stocks,
        start_date=args.start,
        end_date=args.end,
        strategy_class=strategy_class,
        initial_cash=args.cash,
        commission=0.0003,
        threshold=args.threshold,
        max_positions=args.max_positions,
        save_to_db=not args.no_save,
    )

    if result['status'] == 'success':
        print_portfolio_results(result)

        # 基准测试
        if args.benchmark:
            print("\n运行基准测试 (买入持有)...")
            benchmark_result = run_portfolio_backtest(
                stocks=stocks,
                start_date=args.start,
                end_date=args.end,
                strategy_class=SimpleBuyAndHoldPortfolio,
                initial_cash=args.cash,
                commission=0.0003,
                threshold=0,
                max_positions=args.max_positions,
                save_to_db=False,
            )

            if benchmark_result['status'] == 'success':
                print("\n" + "-" * 40)
                print("基准测试结果 (买入持有)")
                print("-" * 40)
                print(f"总收益率: {benchmark_result['total_return']*100:.2f}%")
                print(f"年化收益率: {benchmark_result['annualized_return']*100:.2f}%")
                print(f"夏普比率: {benchmark_result['sharpe_ratio']:.2f}")
                print(f"最大回撤: {benchmark_result['max_drawdown']*100:.2f}%")

                # 计算超额收益
                excess_return = result['total_return'] - benchmark_result['total_return']
                print(f"\n超额收益: {excess_return*100:.2f}%")

        # 保存结果
        if not args.no_save:
            output_path = args.output or f"portfolio_backtest_{args.start}_{args.end}.csv"
            save_results_to_csv(result, output_path)

    else:
        print(f"回测失败: {result.get('error', '未知错误')}")


if __name__ == '__main__':
    main()
