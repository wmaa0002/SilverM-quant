"""
批量回测脚本 V2

支持策略注册表，自动适配不同策略的参数需求。

策略注册表格式:
    '策略文件名': {
        'threshold_required': True/False,  # 是否需要threshold参数
        'min_data_days': 60,               # 最小数据天数
    }

使用示例:
    python batch_backtest_V2.py -l 100 --start 20250101 --end 20251231 --strategy 天宫暴力K策略V1
"""

import sys
import argparse
import os
import logging
import warnings
import json
from pathlib import Path
import inspect
from itertools import product
from dateutil.relativedelta import relativedelta

warnings.warn(
    "batch_backtest_V3.py is deprecated. Use batch_backtest_portfolio.py for true portfolio simulation.",
    DeprecationWarning,
    stacklevel=2
)

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import duckdb
from datetime import datetime
from backtest.engine import BacktestEngine
from scripts.log_utils import setup_logger
from strategies.registry import Registry

# Registry单例
registry = Registry()


ASTOCK3_DB_PATH = project_root / 'data' / 'Astock3.duckdb'


# ============== 策略配置 ==============
# 策略配置已迁移到 strategies/registry.py
# 使用 Registry.get_metadata() 获取策略配置


def get_stock_list_from_db(limit: int = None, industry: str = None, 
                           market_cap_min: float = None, market_cap_max: float = None) -> pd.DataFrame:
    """从数据库获取股票列表（从 dwd_stock_info 读取）
    
    注意: market_cap 字段在 dwd_stock_info 中不存在，
          market_cap_min/max 筛选将被忽略（与旧表行为一致，旧表此字段99.9%为空）
    """
    conn = duckdb.connect(str(ASTOCK3_DB_PATH))
    
    # 字段映射: code←symbol, market_cap 字段已移除
    query = "SELECT symbol AS code, name, industry FROM dwd_stock_info WHERE list_status = 'L'"
    
    if industry:
        query += f" AND industry = '{industry}'"
    # market_cap 筛选: dwd_stock_info 无此字段，跳过（与旧表一致，旧表此字段99.9%为空）
    
    if limit:
        query += f" LIMIT {limit}"
    
    df = conn.execute(query).df()
    conn.close()
    return df


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
        # 未知格式，尝试不带后缀
        return code

def get_data_from_astock3(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """获取单个股票数据"""
    start_date_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    end_date_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    
    # 自动添加交易所后缀
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
    
    if df is not None and len(df) > 0:
        df = df.rename(columns={
            'trade_date': 'date',
            'ts_code': 'code',
            'vol': 'volume'
        })
    
    if df is None or len(df) == 0:
        return None
    
    df = df.rename(columns={
        'date': 'datetime',
        'amount': 'openinterest'
    })
    
    return df


def load_strategy_class(strategy_name: str, use_registry: bool = True):
    """加载策略类
    
    Args:
        strategy_name: 策略名称
        use_registry: 是否优先使用Registry加载 (默认True)
    """
    # 优先使用Registry
    if use_registry:
        strategy_class = registry.get(strategy_name)
        if strategy_class is not None:
            return strategy_class
    
    # 回退到旧方法 (向后兼容) - DEPRECATED: 使用 Registry 替代
    import warnings
    warnings.warn(
        f"策略 '{strategy_name}' 未在注册表中，使用 exec() 加载已废弃。"
        f"请使用 @register 装饰器注册策略。",
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
    """获取策略配置，如果未注册则使用默认值"""
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


def add_strategy_to_engine(engine, strategy_class, threshold: float, strategy_file: str):
    """
    自动检测策略需要的参数并添加策略
    
    根据策略注册表或运行时检测，自动判断需要哪些参数
    """
    # 方法1: 先尝试从注册表获取配置
    config = get_strategy_config(strategy_file)
    
    if not config['threshold_required']:
        # 不需要threshold的策略（如BLK）
        engine.add_strategy(strategy_class)
        return
    
    # 方法2: 运行时检测策略构造参数
    sig = inspect.signature(strategy_class.__init__)
    params = sig.parameters
    
    kwargs = {}
    if 'b1_threshold' in params:
        kwargs['b1_threshold'] = threshold
    elif 'b2_threshold' in params:
        kwargs['b2_threshold'] = threshold
    
    engine.add_strategy(strategy_class, **kwargs)


def run_single_backtest(stock_code: str, stock_name: str, start_date: str, end_date: str,
                        strategy_file: str, threshold: float, initial_cash: float,
                        save_to_db: bool = True, use_registry: bool = True) -> dict:
    """运行单个股票回测"""
    from datetime import date
    
    from_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
    to_date = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
    
    strategy_class = load_strategy_class(strategy_file, use_registry=use_registry)
    
    df = get_data_from_astock3(stock_code, start_date, end_date)
    
    if df is None or len(df) == 0:
        return {
            'code': stock_code,
            'name': stock_name,
            'status': 'no_data',
            'error': '未找到数据'
        }
    
    # 使用策略配置中的最小数据天数
    config = get_strategy_config(strategy_file)
    min_days = config['min_data_days']
    
    if len(df) < min_days:
        return {
            'code': stock_code,
            'name': stock_name,
            'status': 'insufficient_data',
            'error': f'数据不足({len(df)}条，需要{min_days}条)'
        }
    
    try:
        engine = BacktestEngine(
            initial_cash=initial_cash,
            commission=0.0003,
            stamp_duty=0.001,
            slip_page=0.001
        )
        
        engine.add_data(
            df, 
            name=stock_code,
            fromdate=from_date,
            todate=to_date
        )
        
        # 使用新的自动添加策略方法
        add_strategy_to_engine(engine, strategy_class, threshold, strategy_file)
        
        result = engine.run(
            strategy_name=strategy_class.__name__,
            save_results=save_to_db
        )
        
        metrics = result.get('metrics', {})
        
        return {
            'code': stock_code,
            'name': stock_name,
            'status': 'success',
            'run_id': engine.run_id,
            'initial_cash': initial_cash,
            'final_value': result.get('final_value', 0),
            'total_return': metrics.get('total_return', 0),
            'annualized_return': metrics.get('annualized_return', 0),
            'max_drawdown': metrics.get('max_drawdown', 0),
            'sharpe_ratio': metrics.get('sharpe_ratio', 0),
            'win_rate': metrics.get('win_rate', 0),
            'total_trades': metrics.get('total_trades', 0),
            'trade_records': result.get('trade_records', []),
            'daily_pnl': result.get('daily_pnl', []),
        }
        
    except Exception as e:
        import traceback
        return {
            'code': stock_code,
            'name': stock_name,
            'status': 'error',
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def run_batch_backtest(stocks: list, start_date: str, end_date: str,
                        strategy_file: str, threshold: float, initial_cash: float = 100000,
                        save_to_db: bool = True, report_dir: str = None, use_registry: bool = True):
    batch_log_dir = project_root / 'results' / f"batch_{strategy_file}_{start_date}_{end_date}"
    batch_log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = setup_logger(f'batch_{strategy_file}', 'backtest')
    logger.info(f"批量回测开始")
    logger.info(f"策略: {strategy_file}")
    logger.info(f"期间: {start_date} - {end_date}")
    logger.info(f"初始资金: {initial_cash:,.0f}")
    logger.info(f"股票数量: {len(stocks)}")
    
    config = get_strategy_config(strategy_file)
    logger.info(f"策略配置: threshold_required={config['threshold_required']}, min_data_days={config['min_data_days']}")
    
    results = []
    success_count = 0
    fail_count = 0
    no_data_count = 0
    
    for i, stock in enumerate(stocks, 1):
        code = stock.get('code', '')
        name = stock.get('name', '')
        
        logger.info(f"[{i}/{len(stocks)}] {code} {name}...")
        
        result = run_single_backtest(
            code, name, start_date, end_date,
            strategy_file, threshold, initial_cash, save_to_db, use_registry
        )
        
        if result['status'] == 'success':
            success_count += 1
            logger.info(f"✓ {code} 收益率={result['total_return']*100:.2f}%")
        elif result['status'] == 'no_data':
            no_data_count += 1
            logger.info(f"✗ {code} 无数据")
        else:
            fail_count += 1
            logger.warning(f"✗ {code} {result.get('error', '未知错误')}")
        
        results.append(result)
    
    logger.info(f"回测完成 - 总计:{len(stocks)} 成功:{success_count} 无数据:{no_data_count} 失败:{fail_count}")
    
    success_results = [r for r in results if r.get('status') == 'success']
    if success_results:
        avg_return = sum(r['total_return'] for r in success_results) / len(success_results)
        avg_trades = sum(r['total_trades'] for r in success_results) / len(success_results)
        avg_winrate = sum(r['win_rate'] for r in success_results) / len(success_results)
        
        logger.info(f"成功案例统计: 平均收益率={avg_return*100:.2f}%, 平均交易次数={avg_trades:.1f}, 平均胜率={avg_winrate*100:.1f}%")
        
        top5 = sorted(success_results, key=lambda x: x['total_return'], reverse=True)[:5]
        logger.info(f"收益Top5:")
        for r in top5:
            logger.info(f"  {r['code']}: {r['total_return']*100:.2f}%")
    
    results_df = pd.DataFrame(results)
    csv_path = batch_log_dir / f'{strategy_file}_batch_results.csv'
    results_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    logger.info(f"结果已保存到: {csv_path}")
    results_df = pd.DataFrame(results)
    
    return results_df


def parse_param_grid(param_grid_str: str) -> dict:
    """解析参数字符串，如 'threshold:6,8,10 stop_loss_pct:0.02,0.03' -> {'threshold': [6, 8, 10], ...}"""
    param_grid = {}
    if not param_grid_str:
        return param_grid
    
    pairs = param_grid_str.split()
    for pair in pairs:
        if ':' not in pair:
            continue
        key, values_str = pair.split(':', 1)
        values = [float(v) if v.replace('.', '').replace('-', '').isdigit() else v for v in values_str.split(',')]
        param_grid[key.strip()] = values
    
    return param_grid


def run_parameter_sweep(stocks: list, start_date: str, end_date: str,
                        strategy_file: str, param_grid_str: str, initial_cash: float = 100000,
                        save_to_db: bool = False, use_registry: bool = True):
    """运行参数扫描回测"""
    logger = logging.getLogger(f'param_sweep_{strategy_file}')
    
    param_grid = parse_param_grid(param_grid_str)
    if not param_grid:
        logger.error("参数网格为空")
        return None
    
    threshold_values = param_grid.get('threshold', [8.0])
    
    all_results = []
    
    for threshold in threshold_values:
        logger.info(f"运行参数组合: threshold={threshold}")
        
        results_df = run_batch_backtest(
            stocks=stocks,
            start_date=start_date,
            end_date=end_date,
            strategy_file=strategy_file,
            threshold=threshold,
            initial_cash=initial_cash,
            save_to_db=save_to_db,
            report_dir=None,
            use_registry=use_registry
        )
        
        if results_df is not None and len(results_df) > 0:
            success_df = results_df[results_df['status'] == 'success']
            if len(success_df) > 0:
                avg_return = success_df['total_return'].mean()
                avg_sharpe = success_df['sharpe_ratio'].mean() if 'sharpe_ratio' in success_df else 0
                avg_winrate = success_df['win_rate'].mean() if 'win_rate' in success_df else 0
                total_trades = success_df['total_trades'].sum() if 'total_trades' in success_df else 0
                
                all_results.append({
                    'threshold': threshold,
                    'avg_return': avg_return,
                    'sharpe_ratio': avg_sharpe,
                    'win_rate': avg_winrate,
                    'total_trades': total_trades,
                    'success_count': len(success_df),
                    'total_count': len(results_df)
                })
    
    if all_results:
        results_df = pd.DataFrame(all_results)
        output_parameter_comparison(results_df)
        return results_df
    
    return None


def output_parameter_comparison(results_df: pd.DataFrame):
    """输出参数对比表格"""
    if results_df is None or len(results_df) == 0:
        return
    
    print("\n" + "="*80)
    print("参数扫描结果对比")
    print("="*80)
    print(f"{'threshold':>10} {'avg_return':>12} {'sharpe_ratio':>12} {'win_rate':>10} {'total_trades':>14}")
    print("-"*80)
    
    for _, row in results_df.iterrows():
        print(f"{row['threshold']:>10.1f} {row['avg_return']*100:>11.2f}% {row['sharpe_ratio']:>12.2f} {row['win_rate']*100:>9.2f}% {row['total_trades']:>14.0f}")
    
    print("="*80)
    
    best_idx = results_df['avg_return'].idxmax()
    best = results_df.loc[best_idx]
    print(f"最优参数: threshold={best['threshold']:.1f}, 平均收益={best['avg_return']*100:.2f}%")


def parse_walk_forward(walk_forward_str: str) -> dict:
    """解析walk-forward字符串，如 'train:6months test:3months' -> {'train': 6, 'test': 3}"""
    config = {'train': 6, 'test': 3}
    if not walk_forward_str:
        return config
    
    parts = walk_forward_str.split()
    for part in parts:
        if ':' not in part:
            continue
        key, value_str = part.split(':', 1)
        value_str = value_str.strip()
        if 'months' in value_str:
            config[key.strip()] = int(value_str.replace('months', ''))
        elif value_str.isdigit():
            config[key.strip()] = int(value_str)
    
    return config


def run_walk_forward(stocks: list, start_date: str, end_date: str,
                     strategy_file: str, walk_forward_str: str, initial_cash: float = 100000,
                     save_to_db: bool = False, use_registry: bool = True):
    """运行Walk-Forward分析"""
    logger = logging.getLogger(f'walkfwd_{strategy_file}')
    
    wf_config = parse_walk_forward(walk_forward_str)
    train_months = wf_config['train']
    test_months = wf_config['test']
    
    start_dt = datetime.strptime(start_date, '%Y%m%d')
    end_dt = datetime.strptime(end_date, '%Y%m%d')
    
    total_months = (end_dt.year - start_dt.year) * 12 + (end_dt.month - start_dt.month)
    window_months = train_months + test_months
    num_windows = total_months // window_months
    
    if num_windows < 1:
        logger.warning(f"数据期限不足 ({total_months} 个月)，无法进行Walk-Forward分析")
        return None
    
    logger.info(f"Walk-Forward分析: 训练={train_months}月, 测试={test_months}月, 共{num_windows}个窗口")
    
    all_results = []
    
    for i in range(num_windows):
        train_end_dt = start_dt + relativedelta(months=train_months) + relativedelta(months=i * test_months)
        train_start_dt = train_end_dt - relativedelta(months=train_months)
        test_end_dt = train_end_dt + relativedelta(months=test_months)
        
        train_start_str = train_start_dt.strftime('%Y%m%d')
        train_end_str = train_end_dt.strftime('%Y%m%d')
        test_end_str = test_end_dt.strftime('%Y%m%d')
        
        logger.info(f"窗口 {i+1}/{num_windows}: 训练期={train_start_str}-{train_end_str}, 测试期={train_end_str}-{test_end_str}")
        
        train_results_df = run_batch_backtest(
            stocks=stocks,
            start_date=train_start_str,
            end_date=train_end_str,
            strategy_file=strategy_file,
            threshold=8.0,
            initial_cash=initial_cash,
            save_to_db=save_to_db,
            report_dir=None,
            use_registry=use_registry
        )
        
        train_return = 0.0
        if train_results_df is not None and len(train_results_df) > 0:
            success_train = train_results_df[train_results_df['status'] == 'success']
            if len(success_train) > 0:
                train_return = success_train['total_return'].mean()
        
        test_results_df = run_batch_backtest(
            stocks=stocks,
            start_date=train_end_str,
            end_date=test_end_str,
            strategy_file=strategy_file,
            threshold=8.0,
            initial_cash=initial_cash,
            save_to_db=save_to_db,
            report_dir=None,
            use_registry=use_registry
        )
        
        test_return = 0.0
        if test_results_df is not None and len(test_results_df) > 0:
            success_test = test_results_df[test_results_df['status'] == 'success']
            if len(success_test) > 0:
                test_return = success_test['total_return'].mean()
        
        decay_rate = (test_return - train_return) / train_return if train_return != 0 else 0
        
        all_results.append({
            'train_period': f"{train_start_str}-{train_end_str}",
            'test_period': f"{train_end_str}-{test_end_str}",
            'train_return': train_return,
            'test_return': test_return,
            'decay_rate': decay_rate
        })
    
    if all_results:
        results_df = pd.DataFrame(all_results)
        output_walk_forward_comparison(results_df)
        return results_df
    
    return None


def output_walk_forward_comparison(results_df: pd.DataFrame):
    """输出Walk-Forward对比表格"""
    if results_df is None or len(results_df) == 0:
        return
    
    print("\n" + "="*80)
    print("Walk-Forward分析结果: In-Sample vs Out-of-Sample")
    print("="*80)
    print(f"{'训练期':>20} {'测试期':>20} {'训练收益':>12} {'测试收益':>12} {'衰减率':>10}")
    print("-"*80)
    
    for _, row in results_df.iterrows():
        print(f"{row['train_period']:>20} {row['test_period']:>20} {row['train_return']*100:>11.2f}% {row['test_return']*100:>11.2f}% {row['decay_rate']*100:>9.2f}%")
    
    print("="*80)
    
    avg_train = results_df['train_return'].mean()
    avg_test = results_df['test_return'].mean()
    avg_decay = results_df['decay_rate'].mean()
    
    print(f"{'平均':>20} {'':<20} {avg_train*100:>11.2f}% {avg_test*100:>11.2f}% {avg_decay*100:>9.2f}%")


def save_json_results(results: dict, output_path: str):
    """保存结果到JSON文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON结果已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='批量股票策略回测 V2')
    
    parser.add_argument('--stocks', '-s', nargs='+', default=None, 
                       help='股票代码列表，如: 300349 300486')
    parser.add_argument('--stock-file', '-f', default=None,
                       help='股票代码文件（每行一个代码）')
    parser.add_argument('--stock', '-S', default=None, help='股票代码 (单股票模式)'),
    parser.add_argument('--limit', '-l', type=int, default=None,
                       help='从数据库获取的股票数量')
    parser.add_argument('--industry', '-i', type=str, default=None,
                       help='行业过滤')
    parser.add_argument('--start', default='20250101', help='开始日期 YYYYMMDD')
    parser.add_argument('--end', default='20251231', help='结束日期 YYYYMMDD')
    parser.add_argument('--cash', type=float, default=100000, help='初始资金')
    parser.add_argument('--strategy', default='天宫B1策略v1', help='策略文件名')
    parser.add_argument('--threshold', type=float, default=8.0, help='策略阈值')
    parser.add_argument('--no-save', action='store_true', help='不保存到数据库')
    parser.add_argument('--output', '-o', default=None, help='结果输出目录')
    parser.add_argument('--use-registry', dest='use_registry', action='store_true', default=True,
                        help='使用Registry加载策略 (默认启用)')
    parser.add_argument('--no-registry', dest='use_registry', action='store_false',
                        help='禁用Registry,使用旧方法加载策略')
    parser.add_argument('--param-grid', default=None,
                        help='参数网格，如: threshold:6,8,10 stop_loss_pct:0.02,0.03')
    parser.add_argument('--walk-forward', default=None,
                        help='Walk-Forward分析，如: train:6months test:3months')
    parser.add_argument('--output-json', default=None,
                        help='JSON输出文件路径')
    
    args = parser.parse_args()
    
    # 单股票模式 (调用run_backtest)
    if args.stock:
        from run_backtest import run_backtest as run_single
        run_single(args.stock, args.start, args.end, args.cash, args.strategy, args.threshold, not args.no_save)
        return
    
    stocks = None
    
    if args.stocks:
        stocks = [{'code': code, 'name': ''} for code in args.stocks]
    elif args.stock_file:
        with open(args.stock_file, 'r') as f:
            codes = [line.strip() for line in f if line.strip()]
        stocks = [{'code': code, 'name': ''} for code in codes]
    elif args.limit or args.industry:
        stock_df = get_stock_list_from_db(
            limit=args.limit, 
            industry=args.industry
        )
        stocks = stock_df.to_dict('records')
    
    results_df = None
    json_results = {}
    
    if args.param_grid:
        results_df = run_parameter_sweep(
            stocks=stocks,
            start_date=args.start,
            end_date=args.end,
            strategy_file=args.strategy,
            param_grid_str=args.param_grid,
            initial_cash=args.cash,
            save_to_db=not args.no_save,
            use_registry=args.use_registry
        )
        if results_df is not None:
            json_results['param_sweep'] = results_df.to_dict('records')
    
    if args.walk_forward:
        wf_results_df = run_walk_forward(
            stocks=stocks,
            start_date=args.start,
            end_date=args.end,
            strategy_file=args.strategy,
            walk_forward_str=args.walk_forward,
            initial_cash=args.cash,
            save_to_db=not args.no_save,
            use_registry=args.use_registry
        )
        if wf_results_df is not None:
            json_results['walk_forward'] = wf_results_df.to_dict('records')
    
    if not args.param_grid and not args.walk_forward:
        results_df = run_batch_backtest(
            stocks=stocks,
            start_date=args.start,
            end_date=args.end,
            strategy_file=args.strategy,
            threshold=args.threshold,
            initial_cash=args.cash,
            save_to_db=not args.no_save,
            report_dir=args.output,
            use_registry=args.use_registry
        )
        if results_df is not None:
            json_results['batch_backtest'] = results_df.to_dict('records')
    
    if args.output_json and json_results:
        json_results['metadata'] = {
            'strategy': args.strategy,
            'start_date': args.start,
            'end_date': args.end,
            'stock_count': len(stocks) if stocks else 0,
            'threshold': args.threshold,
            'initial_cash': args.cash
        }
        save_json_results(json_results, args.output_json)


if __name__ == '__main__':
    main()
