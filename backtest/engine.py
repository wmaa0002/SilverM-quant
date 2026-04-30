"""
回测引擎 - 基于backtrader的封装
支持多维度回测分析
"""
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Type
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass
import sys

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_manager import DatabaseManager

ASTOCK3_DB_PATH = Path(__file__).parent.parent / 'data' / 'Astock3.duckdb'


@dataclass
class PerformanceMetrics:
    """回测性能指标数据类"""
    total_return: float
    annual_return: float
    benchmark_return: float
    excess_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    volatility: float
    win_rate: float
    profit_loss_ratio: float
    total_trades: int


class BacktestEngine:
    """
    回测引擎
    封装backtrader，提供简洁的回测接口
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        commission: float = 0.0003,
        stamp_duty: float = 0.001,
        slip_page: float = 0.001,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        stock_list: Optional[List[str]] = None,
        stock_file: Optional[str] = None
    ):
        """
        初始化回测引擎
        
        Args:
            initial_cash: 初始资金
            commission: 手续费率
            stamp_duty: 印花税率
            slip_page: 滑点
            start_date: 回测开始日期 (YYYYMMDD格式)
            end_date: 回测结束日期 (YYYYMMDD格式)
            stock_list: 股票代码列表，如 ['000001', '000002']
            stock_file: 股票列表文件路径，每行一个股票代码
        """
        self.initial_cash = initial_cash
        self.commission = commission
        self.stamp_duty = stamp_duty
        self.slip_page = slip_page
        self.start_date = start_date
        self.end_date = end_date
        
        # 股票列表过滤
        self._stock_list = None
        if stock_file:
            self._stock_list = self._load_stock_list_from_file(stock_file)
        elif stock_list:
            self._stock_list = [str(code).strip() for code in stock_list]
        
        # 创建cerebro引擎
        self.cerebro = bt.Cerebro()
        
        # 设置初始资金
        self.cerebro.broker.setcash(initial_cash)
        
        # 设置手续费
        self.cerebro.broker.setcommission(commission=commission)
        
        # 设置滑点
        self.cerebro.broker.set_slippage_perc(slip_page)
        
        # 添加分析器
        self._add_analyzers()
        
        # 数据存储 - 使用Astock3数据库
        self.db = DatabaseManager(str(ASTOCK3_DB_PATH))
        
        # 回测结果
        self.results = None
        self.run_id = None
    
    def _load_stock_list_from_file(self, file_path: str) -> List[str]:
        """从文件加载股票列表"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"股票列表文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            stocks = [line.strip() for line in f if line.strip()]
        return stocks
    
    def get_stock_list(self) -> Optional[List[str]]:
        """获取当前股票列表过滤条件"""
        return self._stock_list
    
    def _add_analyzers(self):
        """添加分析器"""
        # 收益分析
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        # 夏普比率
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        
        # 最大回撤
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
        # 交易统计
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # 时间序列收益
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
        
        # 仓位分析
        self.cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='positions')
    
    def add_data(
        self,
        df: pd.DataFrame,
        name: str = None,
        fromdate: Optional[date] = None,
        todate: Optional[date] = None
    ):
        """
        添加数据
        
        Args:
            df: 包含OHLCV数据的DataFrame
            name: 数据名称（股票代码）
            fromdate: 开始日期 (优先使用实例级start_date)
            todate: 结束日期 (优先使用实例级end_date)
        """
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"数据缺少必需列: {col}")
        
        if 'datetime' not in df.columns:
            if 'date' in df.columns:
                df['datetime'] = pd.to_datetime(df['date'])
            else:
                raise ValueError("数据需要包含'date'或'datetime'列")
        
        df = df.set_index('datetime')
        
        # 删除包含NaN的行
        df = df.dropna()
        
        # 使用实例级日期作为默认值（当方法级参数未指定时）
        effective_fromdate = fromdate if fromdate is not None else self.start_date
        effective_todate = todate if todate is not None else self.end_date
        
        if effective_fromdate:
            if isinstance(effective_fromdate, str):
                effective_fromdate = pd.Timestamp(effective_fromdate)
            df = df[df.index >= effective_fromdate]
        if effective_todate:
            if isinstance(effective_todate, str):
                effective_todate = pd.Timestamp(effective_todate)
            df = df[df.index <= effective_todate]
        
        bt_fromdate = effective_fromdate.to_pydatetime().date() if effective_fromdate else None
        bt_todate = effective_todate.to_pydatetime().date() if effective_todate else None
        
        data = bt.feeds.PandasData(
            dataname=df,
            name=name,
            fromdate=bt_fromdate,
            todate=bt_todate
        )
        
        self.cerebro.adddata(data, name=name)
    
    def add_data_from_db(
        self,
        code: str,
        fromdate: Optional[date] = None,
        todate: Optional[date] = None
    ):
        """从数据库添加数据（使用实例级日期范围进行过滤）"""
        if self._stock_list is not None and code not in self._stock_list:
            return
        
        # 使用实例级日期作为默认值（当方法级参数未指定时）
        effective_fromdate = fromdate if fromdate is not None else self.start_date
        effective_todate = todate if todate is not None else self.end_date
        
        df = self.db.get_daily_price(code, effective_fromdate, effective_todate)
        
        if len(df) == 0:
            raise ValueError(f"数据库中没有 {code} 的数据")
        
        self.add_data(df, name=code, fromdate=fromdate, todate=todate)
    
    def add_strategy(self, strategy_class: Type[bt.Strategy], **kwargs):
        """
        添加策略
        
        Args:
            strategy_class: 策略类
            **kwargs: 策略参数
        """
        self.cerebro.addstrategy(strategy_class, **kwargs)
    
    def run(
        self,
        strategy_name: str = None,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy_name: 策略名称
            save_results: 是否保存结果到数据库
        
        Returns:
            回测结果字典
        """
        print(f"开始回测，初始资金: {self.initial_cash:,.2f}")
        
        # 运行回测
        self.results = self.cerebro.run()
        
        # 获取策略实例
        strat = self.results[0]
        
        # 计算回测结果
        result = self._extract_results(strat)
        
        # 保存到数据库
        if save_results:
            self._save_to_db(strategy_name, result)
        
        # 打印结果
        self._print_results(result)
        
        return result
    
    def _extract_results(self, strat) -> Dict[str, Any]:
        """提取回测结果"""
        result = {
            'initial_value': self.initial_cash,
            'final_value': self.cerebro.broker.getvalue(),
            'total_return': 0.0,
            'trades': [],
            'daily_pnl': [],
            'metrics': {}
        }
        
        # 计算总收益
        result['total_return'] = (
            result['final_value'] - result['initial_value']
        ) / result['initial_value']
        
        # 获取每日收益率并重建权益曲线
        timereturn_analyzer = strat.analyzers.timereturn.get_analysis()
        if timereturn_analyzer:
            daily_data = []
            prev_value = self.initial_cash
            
            for date_str, daily_return in sorted(timereturn_analyzer.items()):
                if daily_return is not None:
                    current_value = prev_value * (1 + daily_return)
                    pnl = current_value - prev_value
                    pnl_pct = daily_return * 100 if prev_value > 0 else 0
                    
                    daily_data.append({
                        'date': date_str,
                        'total_value': current_value,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct
                    })
                    prev_value = current_value
            
            result['daily_pnl'] = daily_data
        
        # 获取分析器结果
        # 收益率
        returns_analyzer = strat.analyzers.returns.get_analysis()
        result['metrics']['total_return'] = returns_analyzer.get('rtot', 0)
        result['metrics']['annualized_return'] = returns_analyzer.get('rnorm', 0)
        
        # 夏普比率
        sharpe_analyzer = strat.analyzers.sharpe.get_analysis()
        result['metrics']['sharpe_ratio'] = sharpe_analyzer.get('sharperatio', 0)
        
        # 最大回撤
        drawdown_analyzer = strat.analyzers.drawdown.get_analysis()
        result['metrics']['max_drawdown'] = drawdown_analyzer.get('max', {}).get('drawdown', 0)
        result['metrics']['max_drawdown_duration'] = drawdown_analyzer.get('max', {}).get('len', 0)
        
        # 交易统计
        trades_analyzer = strat.analyzers.trades.get_analysis()
        if trades_analyzer:
            total_trades = trades_analyzer.get('total', {}).get('total', 0)
            won_trades = trades_analyzer.get('won', {}).get('total', 0)
            lost_trades = trades_analyzer.get('lost', {}).get('total', 0)
            
            result['metrics']['total_trades'] = total_trades
            result['metrics']['winning_trades'] = won_trades
            result['metrics']['losing_trades'] = lost_trades
            result['metrics']['win_rate'] = won_trades / total_trades if total_trades > 0 else 0
            
            # 盈亏统计
            if 'won' in trades_analyzer and 'pnl' in trades_analyzer['won']:
                result['metrics']['avg_profit'] = trades_analyzer['won']['pnl'].get('average', 0)
            if 'lost' in trades_analyzer and 'pnl' in trades_analyzer['lost']:
                result['metrics']['avg_loss'] = trades_analyzer['lost']['pnl'].get('average', 0)
        
        # 获取交易记录
        if hasattr(strat, 'get_trade_df'):
            trades_df = strat.get_trade_df()
            if len(trades_df) > 0:
                result['trades'] = trades_df.to_dict('records')
        elif hasattr(strat, 'trade_records'):
            if len(strat.trade_records) > 0:
                result['trades'] = strat.trade_records
        
        metrics = result['metrics']
        avg_profit = metrics.get('avg_profit', 0)
        avg_loss = abs(metrics.get('avg_loss', 0))
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0
        
        result['performance_metrics'] = PerformanceMetrics(
            total_return=result['total_return'],
            annual_return=metrics.get('annualized_return', 0),
            benchmark_return=0.0,
            excess_return=result['total_return'],
            sharpe_ratio=metrics.get('sharpe_ratio', 0),
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=metrics.get('max_drawdown', 0),
            max_drawdown_duration=metrics.get('max_drawdown_duration', 0),
            volatility=0.0,
            win_rate=metrics.get('win_rate', 0),
            profit_loss_ratio=profit_loss_ratio,
            total_trades=metrics.get('total_trades', 0)
        )
        
        return result
    
    def _save_to_db(self, strategy_name: str, result: Dict):
        """保存结果到数据库 (Astock3)"""
        if not strategy_name:
            strategy_name = 'UnknownStrategy'
        
        # 创建回测记录
        self.run_id = self.db.create_backtest_run(
            strategy_name=strategy_name,
            strategy_params={},
            start_date=date.today(),
            end_date=date.today(),
            universe='custom',
            benchmark='000300.SH',
            initial_capital=self.initial_cash
        )
        
        # 保存交易记录
        if result['trades']:
            trades_df = pd.DataFrame(result['trades'])
            
            # 映射字段名以匹配Astock3表结构
            if 'datetime' not in trades_df.columns and 'date' in trades_df.columns:
                trades_df['datetime'] = pd.to_datetime(trades_df['date'])
            if 'size' not in trades_df.columns and 'volume' in trades_df.columns:
                trades_df['size'] = trades_df['volume']
            if 'amount' not in trades_df.columns and 'price' in trades_df.columns and 'size' in trades_df.columns:
                trades_df['amount'] = trades_df['price'] * trades_df['size']
            
            # 填充默认值
            for col in ['code', 'name', 'commission', 'industry', 'market_cap_group']:
                if col not in trades_df.columns:
                    trades_df[col] = None
            
            # 获取股票代码并填充名称和行业
            stock_codes = []
            for data in self.cerebro.datas:
                if hasattr(data, '_name'):
                    stock_codes.append(data._name)
            
            # 从数据库获取股票信息
            if stock_codes:
                stock_code = stock_codes[0]
                trades_df['code'] = stock_code
                
                # 查询股票信息
                stock_info_df = self.db.conn.execute(
                    f"""
                    SELECT name, industry 
                    FROM dwd_stock_info 
                    WHERE symbol = '{stock_code}'
                    """
                ).fetchone()
                
                if stock_info_df:
                    trades_df['name'] = stock_info_df[0]
                    trades_df['industry'] = stock_info_df[1]
            
            self.db.save_backtest_trades(self.run_id, trades_df)
            print(f"交易记录: {len(result['trades'])} 条 (已保存)")
        
        # 保存每日权益
        if result.get('daily_pnl'):
            daily_df = pd.DataFrame(result['daily_pnl'])
            if not daily_df.empty:
                # 添加run_id
                daily_df['run_id'] = self.run_id
                
                # 确保有positions列
                if 'positions' not in daily_df.columns:
                    daily_df['positions'] = None
                
                # 选择并排序列以匹配表结构
                daily_df = daily_df[['run_id', 'date', 'pnl', 'pnl_pct', 'total_value', 'positions']]
                
                # 保存到数据库
                self.db.save_backtest_daily_pnl(self.run_id, daily_df)
                print(f"每日权益: {len(daily_df)} 条 (已保存)")
        
        # 保存绩效指标
        metrics = result['metrics'].copy()
        
        # 只保留Astock3表中存在的字段
        astock3_fields = {
            'total_return', 'annual_return', 'max_drawdown', 'sharpe_ratio', 
            'win_rate', 'total_trades', 'avg_holding_days'
        }
        
        # 映射字段名以匹配Astock3表结构
        field_mapping = {
            'annualized_return': 'annual_return',
        }
        for old_key, new_key in field_mapping.items():
            if old_key in metrics:
                metrics[new_key] = metrics.pop(old_key)
        
        # 删除不在Astock3表中的字段
        remove_fields = [k for k in metrics.keys() if k not in astock3_fields]
        for field in remove_fields:
            del metrics[field]
        
        self.db.save_backtest_performance(self.run_id, metrics)
        
        print(f"回测结果已保存，run_id: {self.run_id}")
    
    def _print_results(self, result: Dict):
        """打印回测结果"""
        print("\n" + "="*50)
        print("回测结果")
        print("="*50)
        print(f"初始资金: {result['initial_value']:,.2f}")
        print(f"最终资金: {result['final_value']:,.2f}")
        print(f"总收益率: {result['total_return']*100:.2f}%")
        
        metrics = result.get('metrics', {})
        annualized = metrics.get('annualized_return') or 0
        sharpe = metrics.get('sharpe_ratio') or 0
        max_dd = metrics.get('max_drawdown') or 0
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate', 0) or 0
        
        print(f"年化收益率: {annualized*100:.2f}%")
        print(f"夏普比率: {sharpe:.2f}")
        print(f"最大回撤: {max_dd:.2f}%")
        print(f"交易次数: {total_trades}")
        print(f"胜率: {win_rate*100:.2f}%")
        print("="*50)
    
    def plot(self, **kwargs):
        """绘制回测结果"""
        self.cerebro.plot(**kwargs)
    
    def get_run_id(self) -> Optional[str]:
        """获取回测ID"""
        return self.run_id
