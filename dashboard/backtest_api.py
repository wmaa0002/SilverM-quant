"""
Flask API - Backtest回测接口
"""
import sys
import os
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import pandas as pd
import numpy as np
import io
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine
from strategies.registry import Registry
from database.db_manager import DatabaseManager

backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')

batch_tasks = {}

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'Astock3.duckdb')


def get_db():
    """获取数据库连接"""
    return DatabaseManager(str(DB_PATH))


def clean_df_for_json(df):
    """清理DataFrame以便JSON序列化"""
    if df is None or df.empty:
        return []
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object' or str(df[col].dtype).startswith('datetime'):
            df[col] = df[col].apply(lambda x: None if pd.isna(x) else (x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x))
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace({np.nan: None})
    return df.to_dict('records')


@backtest_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """获取可用策略列表

    GET /api/backtest/strategies

    Returns: JSON格式策略列表（从数据库获取）
    """
    try:
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db_strategies = db.list_strategies(status='active')
        strategy_list = [s['name'] for s in db_strategies]
        return jsonify({'strategies': sorted(strategy_list)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/strategies/<path:strategy_name>', methods=['DELETE'])
def delete_strategy(strategy_name):
    """删除策略

    DELETE /api/backtest/strategies/<strategy_name>

    Returns: {
        "success": true
    }
    """
    try:
        registry = Registry()
        success = registry.soft_delete(strategy_name)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': f'策略 {strategy_name} 不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/register-strategies', methods=['POST'])
def register_strategies():
    """扫描并注册所有策略文件

    POST /api/backtest/register-strategies

    Returns: {
        "success": true,
        "loaded": N,
        "failed": N,
        "strategies": [...]
    }
    """
    try:
        from pathlib import Path
        import importlib.util

        strategies_dir = Path(__file__).parent.parent / 'strategies'
        loaded = []
        failed = []

        for py_file in strategies_dir.glob('*.py'):
            if py_file.name.startswith('_') or py_file.name == '策略模板.py':
                continue

            module_name = f"strategies.{py_file.stem}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if not spec or not spec.loader:
                failed.append(py_file.name)
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
                loaded.append(py_file.name)
            except Exception as e:
                failed.append((py_file.name, str(e)))

        # 从数据库重新读取策略（避免单例缓存问题）
        from database.db_manager import DatabaseManager
        db = DatabaseManager()
        db_strategies = db.list_strategies(status='active')
        strategy_list = [s['name'] for s in db_strategies]

        return jsonify({
            'success': True,
            'loaded': len(loaded),
            'failed': len(failed),
            'strategies': sorted(strategy_list)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _load_strategy_files():
    """加载所有策略文件以触发 @register 装饰器"""
    import importlib.util
    from pathlib import Path

    strategies_dir = Path(__file__).parent.parent / 'strategies'
    for py_file in strategies_dir.glob('*.py'):
        if py_file.name.startswith('_'):
            continue
        module_name = f"strategies.{py_file.stem}"
        if module_name in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                pass


@backtest_bp.route('/run', methods=['POST'])
def run_backtest():
    """运行回测

    POST /api/backtest/run
    Body: {
        "strategy_name": "天宫B1策略v2.1",
        "start_date": "20240101",
        "end_date": "20240601",
        "stock_list": ["000001", "000002"],  // optional
        "initial_capital": 100000  // optional
    }

    Returns: {
        "run_id": "abc123",
        "status": "completed",
        "metrics": {...}
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    strategy_name = data.get('strategy_name')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    stock_list = data.get('stock_list')
    initial_capital = data.get('initial_capital', 100000.0)

    if not strategy_name:
        return jsonify({'error': '缺少strategy_name参数'}), 400
    if not start_date:
        return jsonify({'error': '缺少start_date参数'}), 400
    if not end_date:
        return jsonify({'error': '缺少end_date参数'}), 400

    try:
        engine_params = {
            'initial_cash': initial_capital,
            'start_date': start_date,
            'end_date': end_date,
        }
        if stock_list:
            engine_params['stock_list'] = stock_list

        engine = BacktestEngine(**engine_params)

        registry = Registry()
        strategy_class = registry.get(strategy_name)

        if strategy_class is None:
            return jsonify({'error': f'策略 {strategy_name} 未找到'}), 404

        engine.add_strategy(strategy_class)

        if not stock_list:
            db = get_db()
            stock_df = db.conn.execute("""
                SELECT DISTINCT symbol FROM dwd_stock_info
                WHERE delist_date IS NULL
            """).fetchdf()
            stock_list = stock_df['symbol'].tolist() if not stock_df.empty else []

        for stock_code in stock_list:
            try:
                engine.add_data_from_db(stock_code)
            except Exception as e:
                print(f"添加股票 {stock_code} 数据失败: {e}")
                continue

        result = engine.run(strategy_name=strategy_name, save_results=True)

        run_id = engine.get_run_id()

        return jsonify({
            'run_id': run_id,
            'status': 'completed',
            'metrics': {
                'total_return': result.get('total_return', 0),
                'annual_return': result.get('metrics', {}).get('annualized_return', 0),
                'sharpe_ratio': result.get('metrics', {}).get('sharpe_ratio', 0),
                'max_drawdown': result.get('metrics', {}).get('max_drawdown', 0),
                'win_rate': result.get('metrics', {}).get('win_rate', 0),
                'total_trades': result.get('metrics', {}).get('total_trades', 0),
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/history', methods=['GET'])
def get_history():
    """获取回测历史

    GET /api/backtest/history?page=1&limit=10&strategy_name=xxx

    Returns: {
        "runs": [...],
        "total": 100
    }
    """
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    strategy_name = request.args.get('strategy_name')

    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10

    offset = (page - 1) * limit

    try:
        db = get_db()
        all_runs = []

# 2. 查询批量回测结果，按batch_id分组
        batch_query = """
            SELECT 
                batch_id,
                COUNT(*) as total_stocks,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(total_trades) as total_trades,
                AVG(CASE WHEN status = 'success' THEN total_return ELSE NULL END) as avg_return,
                AVG(CASE WHEN status = 'success' THEN sharpe_ratio ELSE NULL END) as avg_sharpe,
                AVG(CASE WHEN status = 'success' THEN max_drawdown ELSE NULL END) as avg_max_drawdown,
                MAX(completed_at) as completed_at
            FROM batch_backtest_results
            GROUP BY batch_id
            ORDER BY completed_at DESC
            LIMIT 50
        """
        batch_df = db.conn.execute(batch_query).fetchdf()

        for _, row in batch_df.iterrows():
            batch_id = row['batch_id']
            total_stocks = int(row['total_stocks']) if pd.notna(row['total_stocks']) else 0
            success_count = int(row['success_count']) if pd.notna(row['success_count']) else 0
            success_rate = success_count / total_stocks if total_stocks > 0 else 0

            batch_run = {
                'run_id': batch_id,
                'type': 'batch',
                'strategy_name': '未知',
                'start_date': None,
                'end_date': None,
                'initial_capital': None,
                'status': 'completed',
                'completed_at': row['completed_at'] if pd.notna(row['completed_at']) else None,
                'total_return': row['avg_return'] if pd.notna(row['avg_return']) else None,
                'sharpe_ratio': row['avg_sharpe'] if pd.notna(row['avg_sharpe']) else None,
                'max_drawdown': row['avg_max_drawdown'] if pd.notna(row['avg_max_drawdown']) else None,
                'total_stocks': total_stocks,
                'success_count': success_count,
                'success_rate': success_rate,
                'total_trades': int(row['total_trades']) if pd.notna(row['total_trades']) else 0
            }

            # 尝试从batch_tasks获取策略名称和日期信息
            if batch_id in batch_tasks and 'params' in batch_tasks[batch_id]:
                params_info = batch_tasks[batch_id]['params']
                batch_run['strategy_name'] = params_info.get('strategy_name', '未知')
                batch_run['start_date'] = params_info.get('start_date')
                batch_run['end_date'] = params_info.get('end_date')
                batch_run['initial_capital'] = params_info.get('initial_capital')

            # 如果strategy_name筛选指定，跳过不匹配的批量结果
            if strategy_name and batch_run['strategy_name'] != strategy_name:
                continue

            all_runs.append(batch_run)

        # 3. 合并后按completed_at排序
        all_runs.sort(key=lambda x: x.get('completed_at') or '', reverse=True)

        # 4. 计算总数并分页
        total = len(all_runs)
        paginated_runs = all_runs[offset:offset + limit]

        return jsonify({
            'runs': paginated_runs,
            'total': total,
            'page': page,
            'limit': limit
        })

    except Exception as e:
        import traceback
        print(f"获取历史记录失败: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


def calculate_metrics_from_daily_pnl(daily_pnl_df):
    """Calculate annualized metrics from daily PnL data.
    
    Args:
        daily_pnl_df: DataFrame with columns: total_value, daily_return, drawdown, cumulative_return
    
    Returns:
        dict with: annualized_return, volatility, sortino_ratio, max_drawdown
    """
    if daily_pnl_df is None or len(daily_pnl_df) == 0:
        return None
    
    import numpy as np
    
    # Get daily returns (they are already decimals, e.g., 0.01 = 1%)
    daily_returns = daily_pnl_df['daily_return'].dropna().values
    
    if len(daily_returns) == 0:
        return None
    
    # 1. Annualized return (compound): (1 + cumulative_return)^(252/trading_days) - 1
    cumulative_return = daily_pnl_df['cumulative_return'].iloc[-1] if 'cumulative_return' in daily_pnl_df.columns else 0
    trading_days = len(daily_pnl_df)
    if trading_days > 0 and cumulative_return > -1:
        years = trading_days / 252
        annualized_return = (1 + cumulative_return) ** (1 / years) - 1 if years > 0 else 0
    else:
        annualized_return = 0
    
    # 2. Volatility: std of daily returns * sqrt(252)
    volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 else 0
    
    # 3. Sharpe ratio: annualized_return / volatility (if volatility > 0)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
    
    # 4. Sortino ratio: use only downside deviation
    # Downside returns are negative returns (returns < 0)
    downside_returns = daily_returns[daily_returns < 0]
    downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_deviation if downside_deviation > 0 else 0
    
    # 5. Max drawdown from daily_pnl (already calculated, just get the max)
    max_drawdown = daily_pnl_df['drawdown'].max() if 'drawdown' in daily_pnl_df.columns else 0
    
    return {
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown
    }


def calculate_batch_metrics(results_df, daily_pnl_df=None):
    """Compute metrics from batch backtest aggregated data.

    Available columns in results_df:
    - status, total_return, annualized_return, max_drawdown, sharpe_ratio
    - win_rate, total_trades, final_value, initial_cash

    Returns:
        dict with 19 keys: total_profit, cumulative_return, annualized_return,
        sharpe_ratio, sortino_ratio (estimated), calmar_ratio, max_drawdown,
        avg_drawdown, volatility (estimated), win_rate, total_trades,
        profit_loss_ratio (estimated), expectancy, + 6 unavailable (None)
    """
    # Initialize default values
    metrics = {
        'total_profit': 0,
        'cumulative_return': 0,
        'annualized_return': 0,
        'sharpe_ratio': 0,
        'sortino_ratio': 0,
        'calmar_ratio': 0,
        'max_drawdown': 0,
        'avg_drawdown': 0,
        'volatility': 0,
        'win_rate': 0,
        'total_trades': 0,
        'profit_loss_ratio': 0,
        'expectancy': 0,
        'expectancy_r': None,
        'best_trade': None,
        'worst_trade': None,
        'avg_profit': None,
        'avg_loss': None,
        'avg_holding_days': None
    }

    if results_df is None or results_df.empty:
        return metrics

    success_df = results_df[(results_df['status'] == 'success') & (results_df['total_trades'] > 0)]

    if success_df.empty:
        return metrics

    # 1. total_profit = sum((final_value - initial_cash)) for success stocks only
    if 'final_value' in success_df.columns and 'initial_cash' in success_df.columns:
        metrics['total_profit'] = (success_df['final_value'] - success_df['initial_cash']).sum()

    # 2. cumulative_return = total_profit / total_initial_cash (derived from total profit)
    if metrics['total_profit'] != 0:
        total_initial_cash = success_df['initial_cash'].sum() if 'initial_cash' in success_df.columns else 0
        if total_initial_cash > 0:
            metrics['cumulative_return'] = metrics['total_profit'] / total_initial_cash

    # 3. annualized_return = mean(annualized_return) for success stocks
    if 'annualized_return' in success_df.columns:
        val = success_df['annualized_return'].mean()
        if pd.notna(val):
            metrics['annualized_return'] = val

    # 4. sharpe_ratio = mean(sharpe_ratio) for success stocks
    if 'sharpe_ratio' in success_df.columns:
        val = success_df['sharpe_ratio'].mean()
        if pd.notna(val):
            metrics['sharpe_ratio'] = val

    if 'max_drawdown' in success_df.columns:
        val = success_df['max_drawdown'].max()
        if pd.notna(val):
            metrics['max_drawdown'] = val / 100 if val > 1 else val

    # 6. avg_drawdown = mean(max_drawdown) for success stocks (convert percentage to decimal)
    if 'max_drawdown' in success_df.columns:
        val = success_df['max_drawdown'].mean()
        if pd.notna(val):
            metrics['avg_drawdown'] = val / 100

    # 7. win_rate = sum(win_rate * total_trades) / sum(total_trades) (weighted)
    if 'win_rate' in success_df.columns and 'total_trades' in success_df.columns:
        total_trades = success_df['total_trades'].sum()
        if total_trades > 0:
            weighted_win_rate = (success_df['win_rate'] * success_df['total_trades']).sum() / total_trades
            if pd.notna(weighted_win_rate):
                metrics['win_rate'] = weighted_win_rate
                metrics['total_trades'] = int(total_trades)

    # 9. calmar_ratio = mean(annualized_return) / mean(max_drawdown)
    avg_return = metrics['annualized_return']
    avg_dd = metrics['avg_drawdown']
    if avg_dd != 0 and avg_return != 0:
        metrics['calmar_ratio'] = avg_return / avg_dd

    # 10. expectancy = mean(total_return) per stock
    if 'total_return' in success_df.columns:
        val = success_df['total_return'].mean()
        if pd.notna(val):
            metrics['expectancy'] = val

    # 11. profit_loss_ratio = estimated from win_rate: win_rate / (1 - win_rate)
    wr = metrics['win_rate']
    if wr > 0 and wr < 1:
        metrics['profit_loss_ratio'] = wr / (1 - wr)

    # Only use daily_pnl_df for metrics if success_df has stocks with trades
    # AND the daily_pnl_df has meaningful data (not just zeros from stocks without trades)
    # For existing batches, daily_pnl_df includes all stocks, so skip it
    if daily_pnl_df is not None and len(daily_pnl_df) > 0 and not success_df.empty:
        # Check if daily_pnl_df has non-zero daily_returns (indicating real trading activity)
        if 'daily_return' in daily_pnl_df.columns:
            non_zero_returns = (daily_pnl_df['daily_return'] != 0).sum()
            total_returns = len(daily_pnl_df)
            # Only use daily_pnl metrics if at least 10% of days have non-zero returns
            # This indicates real trading activity, not just placeholder data
            # For old batches, daily_pnl includes all stocks (not just traded ones), so don't use it
            # Only use daily_pnl for metrics when we can verify it represents only traded stocks
            if False:  # Never use daily_pnl for old batches
                daily_metrics = calculate_metrics_from_daily_pnl(daily_pnl_df)
                if daily_metrics:
                    metrics['annualized_return'] = daily_metrics['annualized_return']
                    metrics['volatility'] = daily_metrics['volatility']
                    metrics['sharpe_ratio'] = daily_metrics['sharpe_ratio']
                    metrics['sortino_ratio'] = daily_metrics['sortino_ratio']
                    metrics['max_drawdown'] = daily_metrics['max_drawdown']  # Already in decimal form (0.01409 = 1.409%)

                    if metrics['avg_drawdown'] != 0:
                        metrics['calmar_ratio'] = metrics['annualized_return'] / metrics['avg_drawdown']

    # Convert numpy types to native Python types for JSON serialization
    for k, v in metrics.items():
        if v is None:
            continue
        if isinstance(v, np.floating):
            metrics[k] = float(v)
        elif isinstance(v, np.integer):
            metrics[k] = int(v)

    return metrics


@backtest_bp.route('/<run_id>', methods=['GET'])
def get_backtest_detail(run_id):
    """获取回测详情

    GET /api/backtest/<run_id>

    Returns: {
        "run_id": "abc123",
        "trades": [...],
        "daily_pnl": [...],
        "metrics": {...}
    }
    
    如果run_id以batch_开头，则返回批量回测汇总结果
    """
    if not run_id:
        return jsonify({'error': '缺少run_id参数'}), 400

    try:
        # 批量回测ID (batch_开头) 返回汇总
        if run_id.startswith('batch_'):
            db = get_db()
            results_df = db.get_batch_backtest_results(run_id)
            
            if results_df is None or results_df.empty:
                return jsonify({'error': '未找到批量回测结果'}), 404
            
            total_stocks = len(results_df)
            success_df = results_df[(results_df['status'] == 'success') & (results_df['total_trades'] > 0)]
            success_count = len(success_df)
            
            success_rate = success_count / total_stocks if total_stocks > 0 else 0
            total_trades = int(results_df['total_trades'].sum()) if 'total_trades' in results_df.columns else 0
            completed_at = results_df['completed_at'].max() if 'completed_at' in results_df.columns and results_df['completed_at'].notna().any() else None

            batch_daily_pnl_raw = db.get_batch_daily_pnl(run_id)
            if batch_daily_pnl_raw is not None and len(batch_daily_pnl_raw) > 0:
                daily_pnl_for_metrics = batch_daily_pnl_raw.copy()
                if 'total_pnl_pct' in daily_pnl_for_metrics.columns:
                    daily_pnl_for_metrics['daily_return'] = daily_pnl_for_metrics['total_pnl_pct'] / 100
            else:
                daily_pnl_for_metrics = None

            batch_metrics = calculate_batch_metrics(results_df, daily_pnl_for_metrics)
            batch_daily_pnl_transformed = []
            for _, row in batch_daily_pnl_raw.iterrows():
                batch_daily_pnl_transformed.append({
                    'date': row.get('date'),
                    'total_value': row.get('total_value'),
                    'daily_pnl': row.get('total_pnl'),
                    'daily_return': row.get('total_pnl_pct', 0) / 100 if row.get('total_pnl_pct') else 0,
                    'cumulative_return': row.get('cumulative_return', 0),
                    'benchmark_return': 0,
                    'excess_return': 0,
                    'drawdown': row.get('drawdown', 0),
                    'cash': 0,
                    'market_value': 0
                })
            batch_daily_pnl = clean_df_for_json(pd.DataFrame(batch_daily_pnl_transformed)) if batch_daily_pnl_transformed else []

            return jsonify({
                'run_id': run_id,
                'type': 'batch',
                'status': 'completed',
                'total_stocks': total_stocks,
                'success_count': success_count,
                'success_rate': success_rate,
                'fail_count': total_stocks - success_count,
                'total_trades': total_trades,
                'completed_at': str(completed_at) if completed_at else None,
                'metrics': batch_metrics,
                'stocks': clean_df_for_json(results_df),
                'daily_pnl': batch_daily_pnl
            })
        
        db = get_db()
        result = db.get_backtest_result(run_id)

        trades = clean_df_for_json(result.get('trades'))
        daily_pnl = clean_df_for_json(result.get('daily_pnl'))

        perf_df = result.get('performance')
        metrics = {}
        if perf_df is not None and not perf_df.empty:
            perf_row = perf_df.iloc[0].to_dict()
            perf_row.pop('run_id', None)
            metrics = {k: v for k, v in perf_row.items() if v is not None and not pd.isna(v)}

        return jsonify({
            'run_id': run_id,
            'type': 'single',
            'trades': trades,
            'daily_pnl': daily_pnl,
            'metrics': metrics
        })

    except Exception as e:
        import traceback
        print(f"获取回测详情失败: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/<run_id>/trades', methods=['GET'])
def get_backtest_trades(run_id):
    """获取回测交易记录

    GET /api/backtest/<run_id>/trades

    Returns: {
        "trades": [...]
    }
    """
    if not run_id:
        return jsonify({'error': '缺少run_id参数'}), 400

    try:
        db = get_db()
        result = db.get_backtest_result(run_id)
        trades = clean_df_for_json(result.get('trades'))

        return jsonify({'trades': trades})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/<run_id>/export', methods=['GET'])
def export_backtest(run_id):
    """导出自测数据

    GET /api/backtest/<run_id>/export?format=csv
    GET /api/backtest/<run_id>/export?format=json

    Query params:
        format: csv (trades only) or json (full data)

    Returns: File download response
    """
    if not run_id:
        return jsonify({'error': '缺少run_id参数'}), 400

    format_type = request.args.get('format', 'csv').lower()
    if format_type not in ('csv', 'json'):
        return jsonify({'error': '不支持的格式，请使用 csv 或 json'}), 400

    try:
        db = get_db()
        result = db.get_backtest_result(run_id)

        # 获取回测基本信息（不包含敏感配置）
        run_info = db.conn.execute("""
            SELECT run_id, strategy_name, start_date, end_date, 
                   initial_capital, status, completed_at
            FROM backtest_run WHERE run_id = ?
        """, [run_id]).fetchdf()

        if run_info.empty:
            return jsonify({'error': '回测记录不存在'}), 404

        date_str = datetime.now().strftime('%Y%m%d')
        filename = f'backtest_{run_id}_{date_str}'

        if format_type == 'csv':
            trades_df = result.get('trades')
            if trades_df is None or trades_df.empty:
                return jsonify({'error': '没有交易记录可导出'}), 404

            csv_df = trades_df.copy()
            for col in csv_df.columns:
                if csv_df[col].dtype == 'object' or str(csv_df[col].dtype).startswith('datetime'):
                    csv_df[col] = csv_df[col].apply(
                        lambda x: '' if pd.isna(x) else (x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
                    )
                elif pd.api.types.is_numeric_dtype(csv_df[col]):
                    csv_df[col] = csv_df[col].fillna('').replace({np.nan: ''})

            csv_output = io.StringIO()
            csv_df.to_csv(csv_output, index=False, encoding='utf-8-sig')
            csv_content = csv_output.getvalue()

            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}.csv',
                    'Content-Type': 'text/csv; charset=utf-8-sig'
                }
            )

        else:
            trades = clean_df_for_json(result.get('trades'))
            daily_pnl = clean_df_for_json(result.get('daily_pnl'))

            perf_df = result.get('performance')
            metrics = {}
            if perf_df is not None and not perf_df.empty:
                perf_row = perf_df.iloc[0].to_dict()
                # 移除敏感字段和内部字段
                sensitive_fields = {'run_id'}
                metrics = {k: v for k, v in perf_row.items() 
                          if v is not None and not pd.isna(v) and k not in sensitive_fields}

            export_data = {
                'run_id': run_id,
                'strategy_name': run_info.iloc[0]['strategy_name'],
                'start_date': str(run_info.iloc[0]['start_date']),
                'end_date': str(run_info.iloc[0]['end_date']),
                'initial_capital': float(run_info.iloc[0]['initial_capital']) if run_info.iloc[0]['initial_capital'] else None,
                'status': run_info.iloc[0]['status'],
                'completed_at': run_info.iloc[0]['completed_at'].strftime('%Y-%m-%d %H:%M:%S') if run_info.iloc[0]['completed_at'] else None,
                'metrics': metrics,
                'trades': trades,
                'daily_pnl': daily_pnl
            }

            json_output = io.StringIO()
            import json as json_module
            json_module.dump(export_data, json_output, ensure_ascii=False, indent=2)
            json_content = json_output.getvalue()

            return Response(
                json_content,
                mimetype='application/json',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}.json',
                    'Content-Type': 'application/json; charset=utf-8'
                }
            )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/batch-run', methods=['POST'])
def batch_run():
    """触发批量回测任务

    POST /api/backtest/batch-run
    Body: {
        "strategy_name": "天宫B1策略v2.1",
        "start_date": "20240101",
        "end_date": "20240601",
        "stock_list": ["000001", "000002"],  // optional
        "initial_capital": 100000,           // optional
        "param_grid": {}                      // optional, 参数网格
    }

    Returns: {
        "task_id": "batch_20240101103000",
        "status": "pending"
    }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    strategy_name = data.get('strategy_name')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    stock_list = data.get('stock_list')
    initial_capital = data.get('initial_capital', 100000.0)
    param_grid = data.get('param_grid')

    if not strategy_name:
        return jsonify({'error': '缺少strategy_name参数'}), 400
    if not start_date:
        return jsonify({'error': '缺少start_date参数'}), 400
    if not end_date:
        return jsonify({'error': '缺少end_date参数'}), 400

    task_id = f"batch_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    batch_tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'message': '任务已创建',
        'started_at': datetime.now().isoformat(),
        'completed_at': None,
        'error_message': None,
        'params': {
            'strategy_name': strategy_name,
            'start_date': start_date,
            'end_date': end_date,
            'stock_list': stock_list,
            'initial_capital': initial_capital,
            'param_grid': param_grid
        }
    }

    thread = threading.Thread(
        target=run_batch_task,
        args=(task_id, strategy_name, start_date, end_date, stock_list, initial_capital, param_grid)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id, 'status': 'pending'})


def run_batch_task(task_id: str, strategy_name: str, start_date: str, end_date: str,
                   stock_list: list = None, initial_capital: float = 100000.0,
                   param_grid: dict = None):
    """后台运行批量回测任务

    T4+T6: 实现实际的批量回测逻辑
    """
    # 动态导入避免循环依赖
    from backtest.strategy_backtest.batch_backtest_portfolio import (
        get_stock_list_from_db, run_portfolio_backtest
    )
    from strategies.registry import Registry

    try:
        batch_tasks[task_id]['status'] = 'running'
        batch_tasks[task_id]['started_at'] = datetime.now().isoformat()
        batch_tasks[task_id]['progress'] = 5
        batch_tasks[task_id]['message'] = '加载股票列表...'

        # 如果没有提供股票列表，从数据库加载
        if stock_list is None or len(stock_list) == 0:
            stocks_df = get_stock_list_from_db()  # 不限制数量
            stocks = [{'code': row['code'], 'name': row['name']} for _, row in stocks_df.iterrows()]
        else:
            # stock_list 是代码列表，需要获取名称
            db = get_db()
            stocks = []
            for code in stock_list:
                try:
                    result = db.conn.execute(
                        "SELECT name FROM dwd_stock_info WHERE symbol = ?",
                        [code]
                    ).fetchone()
                    if result:
                        stocks.append({'code': code, 'name': result[0]})
                    else:
                        stocks.append({'code': code, 'name': code})
                except:
                    stocks.append({'code': code, 'name': code})

        total_stocks = len(stocks)
        batch_tasks[task_id]['message'] = f'开始回测 {total_stocks} 只股票...'

        # 如果有参数扫描，使用 run_parameter_sweep
        if param_grid:
            batch_tasks[task_id]['progress'] = 10
            batch_tasks[task_id]['message'] = '运行参数扫描...'

            results_df = run_parameter_sweep(
                stocks=stocks,
                start_date=start_date,
                end_date=end_date,
                strategy_file=strategy_name,
                param_grid_str=param_grid,
                initial_cash=initial_capital,
                save_to_db=False,
                use_registry=True
            )

            if results_df is not None and len(results_df) > 0:
                db = get_db()
                for _, row in results_df.iterrows():
                    db.save_batch_param_result(
                        batch_id=task_id,
                        param_name='threshold',
                        param_values=[float(row['threshold'])],
                        results={
                            'avg_return': float(row['avg_return']) if pd.notna(row['avg_return']) else 0,
                            'sharpe_ratio': float(row['sharpe_ratio']) if pd.notna(row['sharpe_ratio']) else 0,
                            'win_rate': float(row['win_rate']) if pd.notna(row['win_rate']) else 0,
                            'total_trades': int(row['total_trades']) if pd.notna(row['total_trades']) else 0
                        }
                    )

            batch_tasks[task_id]['status'] = 'completed'
            batch_tasks[task_id]['progress'] = 100
            batch_tasks[task_id]['message'] = '参数扫描完成'
            batch_tasks[task_id]['completed_at'] = datetime.now().isoformat()
            return

        db = get_db()
        threshold = 8.0

        batch_tasks[task_id]['progress'] = 30
        batch_tasks[task_id]['message'] = f'运行组合回测 ({total_stocks}只股票)...'

        registry = Registry()
        strategy_class = registry.get(strategy_name)
        if strategy_class is None:
            batch_tasks[task_id]['status'] = 'failed'
            batch_tasks[task_id]['message'] = f'策略 {strategy_name} 未找到'
            return

        result = run_portfolio_backtest(
            stocks=stocks,
            strategy_class=strategy_class,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_capital,
            threshold=threshold
        )

        # 保存组合结果作为单行记录
        portfolio_result = {
            'code': 'PORTFOLIO',
            'name': '投资组合',
            'status': result.get('status', 'success'),
            'total_return': float(result.get('total_return', 0)) if result.get('total_return') is not None else 0,
            'annualized_return': float(result.get('annualized_return', 0)) if result.get('annualized_return') is not None else 0,
            'max_drawdown': float(result.get('max_drawdown', 0)) if result.get('max_drawdown') is not None else 0,
            'sharpe_ratio': float(result.get('sharpe_ratio', 0)) if result.get('sharpe_ratio') is not None else 0,
            'win_rate': float(result.get('win_rate', 0)) if result.get('win_rate') is not None else 0,
            'total_trades': int(result.get('total_trades', 0)) if result.get('total_trades') is not None else 0,
            'final_value': float(result.get('final_value', 0)) if result.get('final_value') is not None else 0,
            'initial_cash': float(result.get('initial_cash', 0)) if result.get('initial_cash') is not None else 0,
            'error': result.get('error')
        }
        db.save_batch_backtest_result(task_id, portfolio_result)

        # 保存每日pnl数据
        if 'daily_values' in result and 'daily_dates' in result:
            daily_records = []
            initial_value = float(result.get('initial_cash', 0)) if result.get('initial_cash') else 0
            peak_value = initial_value
            cumulative_return = 0
            max_drawdown = 0

            for date_str, value in zip(result['daily_dates'], result['daily_values']):
                if not isinstance(value, (int, float)) or not np.isfinite(value):
                    continue
                date = date_str[:10] if 'T' in date_str else date_str
                pnl = value - initial_value
                cumulative_return = (value - initial_value) / initial_value if initial_value > 0 else 0

                if value > peak_value:
                    peak_value = value
                drawdown = (peak_value - value) / peak_value if peak_value > 0 else 0
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

                daily_records.append({
                    'date': date,
                    'total_value': float(value),
                    'total_pnl': float(pnl),
                    'total_pnl_pct': float((pnl / value * 100) if value > 0 else 0),
                    'cumulative_return': float(cumulative_return),
                    'drawdown': float(drawdown),
                    'positions': None
                })

            if daily_records:
                db.save_batch_daily_pnl(task_id, daily_records)
                print(f"每日汇总已保存: {len(daily_records)}天")

        batch_tasks[task_id]['status'] = 'completed'
        batch_tasks[task_id]['progress'] = 100
        batch_tasks[task_id]['message'] = f'批量回测完成 (共{total_stocks}只)'
        batch_tasks[task_id]['completed_at'] = datetime.now().isoformat()

    except Exception as e:
        import traceback
        batch_tasks[task_id]['status'] = 'failed'
        batch_tasks[task_id]['error_message'] = str(e)
        batch_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        print(f"批量回测任务失败: {task_id}")
        print(traceback.format_exc())


@backtest_bp.route('/batch-task/<task_id>', methods=['GET'])
def get_batch_task_status(task_id):
    """获取批量回测任务状态

    GET /api/backtest/batch-task/<task_id>

    Returns: {
        "task_id": "batch_20240101103000",
        "status": "running",
        "progress": 50,
        "message": "正在处理...",
        "started_at": "2024-01-01T10:30:00",
        "completed_at": null,
        "error_message": null
    }
    """
    if task_id in batch_tasks:
        return jsonify({
            'task_id': task_id,
            'status': batch_tasks[task_id]['status'],
            'progress': batch_tasks[task_id]['progress'],
            'message': batch_tasks[task_id]['message'],
            'started_at': batch_tasks[task_id]['started_at'],
            'completed_at': batch_tasks[task_id]['completed_at'],
            'error_message': batch_tasks[task_id]['error_message']
        })
    else:
        return jsonify({'error': '任务不存在或已过期'}), 404


@backtest_bp.route('/batch-results/<task_id>', methods=['GET'])
def get_batch_results(task_id):
    """获取批量回测任务结果

    GET /api/backtest/batch-results/<task_id>

    Returns: aggregated statistics and per-stock results for a batch backtest
    """
    try:
        db = get_db()

        # 获取所有股票的批量回测结果
        results_df = db.get_batch_backtest_results(task_id)

        if results_df is None or len(results_df) == 0:
            return jsonify({
                'error': '未找到回测结果',
                'task_id': task_id
            }), 404

        # 计算聚合统计
        success_df = results_df[(results_df['status'] == 'success') & (results_df['total_trades'] > 0)]

        total_stocks = len(results_df)
        success_count = len(success_df) if 'status' in results_df.columns else 0
        fail_count = len(results_df[results_df['status'].isin(['error', 'insufficient_data'])]) if 'status' in results_df.columns else 0
        no_data_count = len(results_df[results_df['status'] == 'no_data']) if 'status' in results_df.columns else 0

        # 计算成功案例的统计
        if success_count > 0 and len(success_df) > 0:
            avg_return = float(success_df['total_return'].mean()) if 'total_return' in success_df.columns else 0
            avg_sharpe = float(success_df['sharpe_ratio'].mean()) if 'sharpe_ratio' in success_df.columns else 0
            avg_win_rate = float(success_df['win_rate'].mean()) if 'win_rate' in success_df.columns else 0
            avg_annual_return = float(success_df['annualized_return'].mean()) if 'annualized_return' in success_df.columns else 0
            avg_max_drawdown = float(success_df['max_drawdown'].mean()) if 'max_drawdown' in success_df.columns else 0
            total_trades = int(success_df['total_trades'].sum()) if 'total_trades' in success_df.columns else 0

            # Top5 和 Bottom5
            top5 = success_df.nlargest(5, 'total_return')[['stock_code', 'stock_name', 'total_return', 'sharpe_ratio', 'win_rate']].to_dict('records')
            bottom5 = success_df.nsmallest(5, 'total_return')[['stock_code', 'stock_name', 'total_return', 'sharpe_ratio', 'win_rate']].to_dict('records')
        else:
            avg_return = avg_sharpe = avg_win_rate = avg_annual_return = avg_max_drawdown = 0
            total_trades = 0
            top5 = bottom5 = []

        # 获取参数扫描结果（如果有）
        param_results = None
        param_df = db.get_batch_param_results(task_id)
        if param_df is not None and len(param_df) > 0:
            param_results = param_df.to_dict('records') if param_df is not None and len(param_df) > 0 else None

        error_stocks = results_df[results_df['status'].isin(['error', 'insufficient_data'])]
        error_stocks_list = error_stocks[['stock_code', 'stock_name', 'status', 'error_message']].to_dict('records') if len(error_stocks) > 0 else []

        return jsonify({
            'task_id': task_id,
            'total_stocks': total_stocks,
            'success_count': success_count,
            'fail_count': fail_count,
            'no_data_count': no_data_count,
            'success_rate': success_count / total_stocks if total_stocks > 0 else 0,
            'avg_return': avg_return,
            'avg_sharpe': avg_sharpe,
            'avg_win_rate': avg_win_rate,
            'avg_annual_return': avg_annual_return,
            'avg_max_drawdown': avg_max_drawdown,
            'total_trades': total_trades,
            'top5_stocks': top5,
            'bottom5_stocks': bottom5,
            'param_results': param_results,
            'error_stocks': error_stocks_list,
            'stocks': results_df[['stock_code', 'stock_name', 'status', 'total_return', 'sharpe_ratio', 'win_rate', 'total_trades', 'error_message']].to_dict('records')
        })

    except Exception as e:
        import traceback
        print(f"获取批量回测结果失败: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@backtest_bp.route('/batch-task/<task_id>', methods=['DELETE'])
def cancel_batch_task(task_id):
    """取消批量回测任务

    DELETE /api/backtest/batch-task/<task_id>
    """
    if task_id in batch_tasks:
        batch_tasks[task_id]['status'] = 'cancelled'
        batch_tasks[task_id]['message'] = '任务已取消'
        batch_tasks[task_id]['completed_at'] = datetime.now().isoformat()
        return jsonify({'task_id': task_id, 'status': 'cancelled'})
    else:
        return jsonify({'error': '任务不存在或已过期'}), 404