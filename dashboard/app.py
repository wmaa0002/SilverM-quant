import os
import sys

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import duckdb
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import akshare as ak

# Agent API路由
from dashboard.agent_api import agent_bp
from dashboard.data_update_api import data_update_bp
from dashboard.backtest_api import backtest_bp

# Vue 前端 build 产物路径
FRONTEND_DIST = os.path.join(
    os.path.dirname(__file__), 
    '..', 'frontend', 'dist'
)

app = Flask(__name__)
CORS(app)

# 注册蓝图
app.register_blueprint(agent_bp)
app.register_blueprint(data_update_bp)
app.register_blueprint(backtest_bp)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'Astock3.duckdb')

# 策略ID到中文名称映射
STRATEGY_NAME_MAP = {
    'b1': 'B1策略',
    'b2': 'B2策略',
    'blk': 'BLK策略',
    'blkB2': 'BLKB2策略',
    'dl': 'DL策略',
    'dz30': 'DZ30策略',
    'scb': 'SCB策略',
}
SELL_STRATEGY_NAME_MAP = {
    's1_full': 'S1满仓信号',
    's1_half': 'S1半仓信号',
    '跌破多空线': '跌破多空线',
    '止损': '止损信号',
}

def get_db():
    return duckdb.connect(DB_PATH, read_only=True)

def get_latest_trading_date():
    db = get_db()
    try:
        latest = db.execute("SELECT MAX(trade_date) FROM dwd_daily_price").fetchone()[0]
        if latest:
            return latest.strftime('%Y-%m-%d')
    finally:
        db.close()
    return datetime.now().strftime('%Y-%m-%d')

def code_to_ts_code(code: str) -> str:
    """转换股票代码为tushare格式"""
    code = str(code)
    if code.startswith('6'):
        return f"{code}.SH"
    else:
        return f"{code}.SZ"

def clean_df_for_json(df):
    for col in df.columns:
        if df[col].dtype == 'object' or str(df[col].dtype).startswith('datetime'):
            df[col] = df[col].apply(lambda x: None if pd.isna(x) else (x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x))
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].replace({np.nan: None})
    return df

def map_sell_reason(reason):
    """将卖出原因映射为可读信号名称"""
    if not reason:
        return '信号卖出'
    
    reason_map = {
        '止损': '止损信号',
        '跌破多空线': '跌破多空线信号',
        '多空线信号': '多空线信号',
        '趋势反转': '趋势反转信号',
        '止盈': '止盈信号',
        '仓位调整': '仓位调整信号',
    }
    
    # 检查是否包含关键词
    for key, value in reason_map.items():
        if key in str(reason):
            return value
    
    return f'信号卖出({reason})'

@app.route('/')
def index():
    """Vue 前端首页"""
    if os.path.exists(os.path.join(FRONTEND_DIST, 'index.html')):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    return render_template('index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """Vue 静态资源 (JS/CSS/图片等)"""
    # API 请求不归我们管
    if filename.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    
    # 尝试从 Vue build 目录提供静态文件
    file_path = os.path.join(FRONTEND_DIST, filename)
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        return send_from_directory(FRONTEND_DIST, filename)
    
    # 非静态文件请求（如Vue路由 /signals, /positions 等）
    # 由 index.html 接管，让 Vue Router 处理
    if os.path.exists(os.path.join(FRONTEND_DIST, 'index.html')):
        return send_from_directory(FRONTEND_DIST, 'index.html')
    
    return jsonify({'error': 'Not found'}), 404

@app.route('/agent')
def agent():
    return send_from_directory(FRONTEND_DIST, 'index.html')

@app.route('/agent/history')
def agent_history():
    return send_from_directory(FRONTEND_DIST, 'index.html')

@app.route('/data-update')
def data_update():
    return send_from_directory(FRONTEND_DIST, 'index.html')

@app.route('/api/positions')
def api_positions():
    db = get_db()
    try:
        # 获取排序参数，默认按buy_date DESC
        sort = request.args.get('sort', 'buy_date')
        order = request.args.get('order', 'desc')

        # 验证排序字段白名单
        allowed_sort_fields = {'buy_date', 'profit_pct', 'profit_loss', 'current_price', 'buy_price', 'name', 'code'}
        if sort not in allowed_sort_fields:
            sort = 'buy_date'

        # 验证排序方向
        order = order.upper() if order.upper() in ('ASC', 'DESC') else 'DESC'

        df = db.execute(f"""
            SELECT 
                id, code, name, strategy,
                signal_date, buy_date, shares, buy_price,
                buy_change_pct, buy_score_b1, buy_score_b2,
                current_price, profit_loss, profit_pct,
                stop_loss_pct, status, notes,
                ROUND(shares * buy_price * 0.9998, 2) as position_amount
            FROM positions 
            WHERE status = 'holding'
            ORDER BY {sort} {order}
        """).df()
        
        latest_date = get_latest_trading_date()
        if latest_date and not df.empty:
            # 优化：批量查询所有持仓股票的最新价格，避免 N+1 查询
            codes = df['code'].tolist()
            if codes:
                # 转换codes为tushare格式
                ts_codes = [code_to_ts_code(c) for c in codes]
                price_df = db.execute("""
                    SELECT ts_code, close 
                    FROM dwd_daily_price 
                    WHERE trade_date = ? AND ts_code IN (""" + ','.join(['?' for _ in ts_codes]) + """)
                """, [latest_date] + ts_codes).df()
                
                # 创建价格映射
                price_map = dict(zip(price_df['ts_code'], price_df['close']))
                
                for idx, row in df.iterrows():
                    ts_code = code_to_ts_code(row['code'])
                    current_price = price_map.get(ts_code)
                    if current_price is not None:
                        df.at[idx, 'current_price'] = current_price
                        if row['buy_price']:
                            profit_pct = (current_price - row['buy_price']) / row['buy_price'] * 100
                            profit_loss = (current_price - row['buy_price']) * row['shares']
                            df.at[idx, 'profit_pct'] = round(profit_pct, 2)
                            df.at[idx, 'profit_loss'] = round(profit_loss, 2)
        
        df = clean_df_for_json(df)
        positions = df.to_dict('records')
        
        # 查询历史交易总盈亏
        history_profit = db.execute("SELECT COALESCE(SUM(profit_loss), 0) FROM positions WHERE status = 'sold'").fetchone()[0]
        
        total_capital = 500000  # 总资金
        total_value = sum(p['current_price'] * p['shares'] if p['current_price'] else 0 for p in positions)
        total_cost = sum(p['buy_price'] * p['shares'] if p['buy_price'] else 0 for p in positions)
        holding_profit = total_value - total_cost  # 持仓盈亏
        total_profit = holding_profit + history_profit  # 总盈亏 = 持仓盈亏 + 历史盈亏
        available_cash = total_capital - total_value + total_profit  # 可用资金 = 50万 - 持仓市值 + 总盈亏
        
        return jsonify({
            'positions': positions,
            'summary': {
                'total_value': round(total_value, 2),
                'total_cost': round(total_cost, 2),
                'holding_profit': round(holding_profit, 2),
                'history_profit': round(history_profit, 2),
                'total_profit': round(total_profit, 2),
                'profit_pct': round(total_profit / total_cost * 100, 2) if total_cost > 0 else 0,
                'count': len(positions),
                'available_cash': round(available_cash, 2)
            }
        })
    finally:
        db.close()

@app.route('/api/history')
def api_history():
    db = get_db()
    try:
        df = db.execute("""
            SELECT 
                code, name, strategy,
                buy_date, buy_price, shares,
                sell_date, sell_price, sell_reason,
                profit_loss, profit_pct
            FROM positions 
            WHERE status = 'sold'
            ORDER BY sell_date DESC
        """).df()
        
        df['buy_signal_type'] = df['strategy'].apply(lambda x: x if x else '趋势择时')
        df['sell_signal_type'] = df['sell_reason'].apply(lambda x: map_sell_reason(x) if x else '信号卖出')
        
        df = clean_df_for_json(df)
        history = df.to_dict('records')
        
        total_profit = sum(p['profit_loss'] if p['profit_loss'] else 0 for p in history)
        win_count = len([p for p in history if p['profit_loss'] and p['profit_loss'] > 0])
        loss_count = len([p for p in history if p['profit_loss'] and p['profit_loss'] < 0])
        
        win_total = sum(p['profit_loss'] for p in history if p['profit_loss'] and p['profit_loss'] > 0)
        loss_total = abs(sum(p['profit_loss'] for p in history if p['profit_loss'] and p['profit_loss'] < 0))
        avg_win = win_total / win_count if win_count > 0 else 0
        avg_loss = loss_total / loss_count if loss_count > 0 else 0
        profit_loss_ratio = round(avg_win / avg_loss, 2) if avg_loss > 0 else 0
        
        return jsonify({
            'history': history,
            'summary': {
                'total_trades': len(history),
                'total_profit': round(total_profit, 2),
                'win_count': win_count,
                'loss_count': loss_count,
                'win_rate': round(win_count / len(history) * 100, 2) if len(history) > 0 else 0,
                'profit_loss_ratio': profit_loss_ratio
            }
        })
    finally:
        db.close()

from scripts.frontend_analysis.history_metrics import calculate_all_metrics

@app.route('/api/history/analysis')
def api_history_analysis():
    """综合分析历史交易数据"""
    try:
        return jsonify(calculate_all_metrics())
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/signals')
def api_signals():
    db = get_db()
    try:
        latest_date = db.execute("SELECT MAX(date) FROM daily_signals").fetchone()[0]
        
        if not latest_date:
            return jsonify({'signals': [], 'date': None})
        
        date_str = latest_date.strftime('%Y-%m-%d') if hasattr(latest_date, 'strftime') else str(latest_date)
        
        df = db.execute("SELECT * FROM daily_signals WHERE date = ?", [latest_date]).df()
        
        if df.empty:
            return jsonify({'signals': [], 'date': date_str, 'buy_count': 0, 'sell_count': 0})
        
        buy_signal_cols = [c for c in df.columns if c.startswith('signal_buy_')]
        sell_signal_cols = [c for c in df.columns if c in ('signal_s1_full', 'signal_s1_half', 'signal_跌破多空线', 'signal_止损')]
        
        result = []
        buy_count = 0
        sell_count = 0
        
        for _, row in df.iterrows():
            buy_signals = []
            sell_signals = []
            
            for col in buy_signal_cols:
                if row[col] is True or row[col] == 1:
                    strategy_id = col.replace('signal_buy_', '')
                    strategy_name = STRATEGY_NAME_MAP.get(strategy_id, strategy_id)
                    score_col = f'score_{strategy_id}'
                    score = row.get(score_col, 0) or 0
                    buy_signals.append({'strategy': strategy_name, 'score': round(score, 2)})
            
            for col in sell_signal_cols:
                if row[col] is True or row[col] == 1:
                    sell_key = col.replace('signal_', '')
                    strategy_name = SELL_STRATEGY_NAME_MAP.get(sell_key, sell_key)
                    sell_signals.append({'strategy': strategy_name, 'score': round(row.get(f'score_{sell_key}', 0) or 0, 2)})
            
            if buy_signals or sell_signals:
                if buy_signals:
                    buy_count += 1
                if sell_signals:
                    sell_count += 1
                result.append({
                    'code': row['code'],
                    'name': row['name'],
                    'close': round(row['close'], 2) if pd.notna(row['close']) else None,
                    'change_pct': round(row['change_pct'], 2) if pd.notna(row['change_pct']) else None,
                    'open': round(row['open'], 2) if pd.notna(row['open']) else None,
                    'high': round(row['high'], 2) if pd.notna(row['high']) else None,
                    'low': round(row['low'], 2) if pd.notna(row['low']) else None,
                    'volume': int(row['volume']) if pd.notna(row['volume']) else None,
                    'buy_signals': buy_signals,
                    'sell_signals': sell_signals,
                })
        
        result.sort(key=lambda x: max([s['score'] for s in x['buy_signals']] or [0], default=0), reverse=True)
        
        return jsonify({
            'signals': result,
            'date': date_str,
            'buy_count': buy_count,
            'sell_count': sell_count
        })
    finally:
        db.close()

@app.route('/api/equity-curve')
def api_equity_curve():
    import signal
        
    def timeout_handler(signum, frame):
        raise TimeoutError("akshare API timeout")
    
    db = get_db()
    try:
        portfolio = db.execute("""
            SELECT 
                date,
                total_value,
                init_cash,
                position_ratio,
                closed_pnl,
                available_cash,
                (total_pnl - closed_pnl) AS position_pnl
            FROM portfolio_daily
            ORDER BY date
        """).fetchall()
        
        if not portfolio:
            dates = []
            for i in range(30):
                d = datetime.now() - timedelta(days=29-i)
                dates.append(d.strftime('%Y-%m-%d'))
            mock_values = [500000] * 30
            return jsonify({
                'dates': dates,
                'values': mock_values,
                'benchmark': [500000] * 30,
                'total_return': 0,
                'annotations': {
                    'peak': {'date': dates[0], 'value': 500000, 'return_pct': 0},
                    'trough': {'date': dates[-1], 'value': 500000},
                    'max_drawdown': {'date': None, 'pct': 0}
                }
            })
        
        dates = []
        values = []
        position_ratio_list = []
        closed_pnl_list = []
        available_cash_list = []
        position_pnl_list = []
        initial_value = 500000
        
        for p in portfolio:
            date, total_value, init_cash, position_ratio, closed_pnl, available_cash, position_pnl = p
            d_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            dates.append(d_str)
            values.append(float(total_value) if total_value else 500000)
            position_ratio_list.append(round(float(position_ratio), 2) if position_ratio else 0)
            closed_pnl_list.append(round(float(closed_pnl), 2) if closed_pnl else 0)
            available_cash_list.append(round(float(available_cash), 2) if available_cash else 0)
            position_pnl_list.append(round(float(position_pnl), 2) if position_pnl else 0)
        
        # initial_value 从第一行的 init_cash 读取
        if portfolio and portfolio[0][2]:
            initial_value = float(portfolio[0][2])
        
        benchmark_values = []
        try:
            # 直接从数据库读取上证指数数据，无需外部API
            index_data = db.execute("""
                SELECT trade_date, close FROM dwd_index_daily 
                WHERE index_code = '000001.SH' 
                AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date
            """, [dates[0], dates[-1]]).fetchall()
            
            if index_data:
                index_map = {str(row[0]): float(row[1]) for row in index_data}
                first_close = index_map.get(dates[0])
                
                if first_close and first_close > 0:
                    for d in dates:
                        close = index_map.get(d)
                        if close:
                            benchmark_values.append(initial_value * close / first_close)
                        else:
                            benchmark_values.append(benchmark_values[-1] if benchmark_values else initial_value)
                else:
                    benchmark_values = [initial_value] * len(dates)
            else:
                benchmark_values = [initial_value] * len(dates)
        except Exception as e:
            print(f"获取上证指数失败: {e}")
            benchmark_values = [initial_value] * len(dates)
        
        current_value = values[-1] if values else initial_value
        total_return = (current_value - initial_value) / initial_value * 100 if initial_value > 0 else 0
        
        # ========== 计算关键指标 ==========
        initial_value_const = 500000

        # 最大收益率和日期 (峰值)
        peak_value = max(values)
        peak_idx = values.index(peak_value)
        peak_date = dates[peak_idx]
        peak_return = (peak_value - initial_value_const) / initial_value_const * 100

        # 最低市值和日期 (谷值)
        trough_value = min(values)
        trough_idx = values.index(trough_value)
        trough_date = dates[trough_idx]

        # 最大回撤计算
        max_drawdown = 0
        max_drawdown_date = None
        peak_so_far = initial_value_const

        for i, (d, v) in enumerate(zip(dates, values)):
            if v > peak_so_far:
                peak_so_far = v
            drawdown = (peak_so_far - v) / peak_so_far * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_date = d

        return jsonify({
            'dates': dates,
            'values': [round(v, 2) for v in values],
            'benchmark': [round(v, 2) for v in benchmark_values],
            'total_return': round(total_return, 2),
            'annotations': {
                'peak': {
                    'date': peak_date,
                    'value': round(peak_value, 2),
                    'return_pct': round(peak_return, 2)
                },
                'trough': {
                    'date': trough_date,
                    'value': round(trough_value, 2)
                },
                'max_drawdown': {
                    'date': max_drawdown_date,
                    'pct': round(max_drawdown, 2)
                }
            },
            'position_ratio': position_ratio_list,
            'closed_pnl': closed_pnl_list,
            'available_cash': available_cash_list,
            'position_pnl': position_pnl_list
        })
    finally:
        db.close()

@app.route('/api/strategy-comparison')
def api_strategy_comparison():
    """
    获取策略对比数据

    从 portfolio_daily_strategy 表获取各策略的真实每日表现数据。
    """
    db = get_db()
    try:
        INITIAL_CAPITAL = 500000.0

        strategies = db.execute("""
            SELECT DISTINCT strategy
            FROM portfolio_daily_strategy
            WHERE strategy IS NOT NULL
            ORDER BY strategy
        """).fetchall()

        if not strategies:
            return jsonify({
                'strategies': [],
                'dates': [],
                'curves': {},
                'metrics': {}
            })

        colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

        strategy_data = {}

        for i, (strategy_name,) in enumerate(strategies):
            daily_data = db.execute("""
                SELECT date, total_pnl, closed_pnl, position_pnl, trade_count
                FROM portfolio_daily_strategy
                WHERE strategy = ?
                ORDER BY date
            """, [strategy_name]).fetchall()

            if not daily_data:
                continue

            dates = []
            values = []
            cumulative_pnl = 0.0

            for row in daily_data:
                date, total_pnl, closed_pnl, position_pnl, trade_count = row
                date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
                dates.append(date_str)

                if total_pnl is not None:
                    cumulative_pnl = float(total_pnl)

                portfolio_value = INITIAL_CAPITAL + cumulative_pnl
                values.append(round(portfolio_value, 2))

            if not dates:
                continue

            strategy_data[strategy_name] = {
                'dates': dates,
                'values': values,
                'trade_count': sum(row[4] for row in daily_data if row[4] is not None),
                'color': colors[i % len(colors)]
            }

        all_dates = set()
        for sd in strategy_data.values():
            all_dates.update(sd['dates'])

        sorted_dates = sorted(all_dates)
        date_to_idx = {d: i for i, d in enumerate(sorted_dates)}

        curves = {}
        metrics = {}

        for strategy_name, sd in strategy_data.items():
            aligned_values = []
            last_value = INITIAL_CAPITAL
            date_to_value = dict(zip(sd['dates'], sd['values']))

            for date_str in sorted_dates:
                if date_str in date_to_value:
                    v = date_to_value[date_str]
                    if v is not None:
                        last_value = v
                aligned_values.append(last_value)

            values = aligned_values

            valid_values = [v for v in values if v is not None]
            if not valid_values:
                continue

            final_value = valid_values[-1]
            total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL

            peak = INITIAL_CAPITAL
            max_drawdown = 0
            for v in valid_values:
                if v > peak:
                    peak = v
                drawdown = (peak - v) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

            if len(valid_values) > 1:
                returns = [(valid_values[j] - valid_values[j-1]) / valid_values[j-1] for j in range(1, len(valid_values)) if valid_values[j-1] != 0]
                if returns:
                    avg_ret = sum(returns) / len(returns)
                    variance = sum((r - avg_ret) ** 2 for r in returns) / len(returns)
                    std_dev = variance ** 0.5
                    sharpe_ratio = avg_ret / std_dev * (252 ** 0.5) if std_dev > 0 else 0
                else:
                    sharpe_ratio = 0
            else:
                sharpe_ratio = 0

            curves[strategy_name] = {
                'data': values,
                'initial_value': INITIAL_CAPITAL,
                'color': sd['color']
            }

            metrics[strategy_name] = {
                'total_return': round(total_return, 4),
                'annualized_return': round(total_return * 252 / len(valid_values), 4) if valid_values else 0,
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown, 4),
                'win_rate': 0,
                'total_trades': int(sd['trade_count'])
            }

        return jsonify({
            'strategies': [s[0] for s in strategies if s[0] in curves],
            'dates': sorted_dates,
            'initial_value': INITIAL_CAPITAL,
            'curves': curves,
            'metrics': metrics
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/api/stats')
def api_stats():
    db = get_db()
    try:
        holding_count = db.execute("SELECT COUNT(*) FROM positions WHERE status = 'holding'").fetchone()[0]
        sold_count = db.execute("SELECT COUNT(*) FROM positions WHERE status = 'sold'").fetchone()[0]
        
        latest_date = db.execute("SELECT MAX(date) FROM daily_signals").fetchone()[0]
        buy_signals_count = 0
        if latest_date:
            buy_signals_count = db.execute("""
                SELECT COUNT(*) FROM daily_signals 
                WHERE date = ? AND (signal_buy_b1 = true OR signal_buy_b2 = true)
            """, [latest_date]).fetchone()[0]
        
        return jsonify({
            'holding_count': holding_count,
            'sold_count': sold_count,
            'today_buy_signals': buy_signals_count,
            'latest_date': latest_date.strftime('%Y-%m-%d') if latest_date else None
        })
    finally:
        db.close()

@app.route('/api/multi-signal-resonance')
def api_multi_signal_resonance():
    """获取多信号共振股票"""
    date_str = request.args.get('date')
    if not date_str:
        # 默认前一天
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    db = get_db()
    try:
        result = db.execute("""
            SELECT code, name,
                   signal_buy_b1, signal_buy_b2, signal_buy_blk, signal_buy_dl,
                   signal_buy_dz30, signal_buy_scb, signal_buy_blkB2,
                   close, change_pct
            FROM daily_signals
            WHERE date = ?
            AND (CAST(signal_buy_b1 AS INT) + CAST(signal_buy_b2 AS INT) + 
                 CAST(signal_buy_blk AS INT) + CAST(signal_buy_dl AS INT) + 
                 CAST(signal_buy_dz30 AS INT) + CAST(signal_buy_scb AS INT) + 
                 CAST(signal_buy_blkB2 AS INT)) >= 2
            ORDER BY (CAST(signal_buy_b1 AS INT) + CAST(signal_buy_b2 AS INT) + 
                      CAST(signal_buy_blk AS INT) + CAST(signal_buy_dl AS INT) + 
                      CAST(signal_buy_dz30 AS INT) + CAST(signal_buy_scb AS INT) + 
                      CAST(signal_buy_blkB2 AS INT)) DESC,
                     close DESC
        """, [date_str]).fetchall()
        
        signal_names = ['B1', 'B2', 'BLK', 'DL', 'DZ30', 'SCB', 'BLKB2']
        data = []
        for row in result:
            signals = [signal_names[i] for i, v in enumerate(row[2:9]) if v]
            data.append({
                'code': row[0],
                'name': row[1],
                'signal_count': len(signals),
                'signals': signals,
                'close': float(row[9]) if row[9] else 0,
                'change_pct': float(row[10]) if row[10] else 0
            })
        
        return jsonify({
            'date': date_str,
            'stocks': data,
            'count': len(data)
        })
    finally:
        db.close()

@app.route('/api/multi-signal-trend')
def api_multi_signal_trend():
    """获取多信号共振趋势数据"""
    db = get_db()
    try:
        result = db.execute("""
            SELECT date,
                   SUM(CAST(signal_buy_b1 AS INT)) as b1_count,
                   SUM(CAST(signal_buy_b2 AS INT)) as b2_count,
                   SUM(CAST(signal_buy_blk AS INT)) as blk_count,
                   SUM(CAST(signal_buy_dl AS INT)) as dl_count,
                   SUM(CAST(signal_buy_dz30 AS INT)) as dz30_count,
                   SUM(CAST(signal_buy_scb AS INT)) as scb_count,
                   SUM(CAST(signal_buy_blkB2 AS INT)) as blkB2_count,
                   COUNT(*) as total_count
            FROM daily_signals
            WHERE (CAST(signal_buy_b1 AS INT) + CAST(signal_buy_b2 AS INT) + 
                   CAST(signal_buy_blk AS INT) + CAST(signal_buy_dl AS INT) + 
                   CAST(signal_buy_dz30 AS INT) + CAST(signal_buy_scb AS INT) + 
                   CAST(signal_buy_blkB2 AS INT)) >= 2
            GROUP BY date
            ORDER BY date
        """).fetchall()
        
        dates = []
        total_counts = []
        signal_data = {
            'B1': [], 'B2': [], 'BLK': [], 'DL': [], 'DZ30': [], 'SCB': [], 'BLKB2': []
        }
        
        for row in result:
            date_str = row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0])
            dates.append(date_str)
            total_counts.append(int(row[8]))
            signal_data['B1'].append(int(row[1]))
            signal_data['B2'].append(int(row[2]))
            signal_data['BLK'].append(int(row[3]))
            signal_data['DL'].append(int(row[4]))
            signal_data['DZ30'].append(int(row[5]))
            signal_data['SCB'].append(int(row[6]))
            signal_data['BLKB2'].append(int(row[7]))
        
        return jsonify({
            'dates': dates,
            'total_counts': total_counts,
            'signal_data': signal_data
        })
    finally:
        db.close()


@app.route('/multi-signal-resonance')
def multi_signal_resonance():
    return send_from_directory(FRONTEND_DIST, 'index.html')


@app.route('/api/multi-signal-resonance/dates')
def api_multi_signal_resonance_dates():
    """API: 获取多策略共振可用的日期列表"""
    db = get_db()
    try:
        dates = db.execute("SELECT DISTINCT date FROM daily_signals ORDER BY date DESC").fetchall()
        return jsonify({
            'dates': [{'value': d[0].strftime('%Y-%m-%d'), 'label': d[0].strftime('%Y-%m-%d')} for d in dates]
        })
    finally:
        db.close()


if __name__ == '__main__':
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    print("启动Dashboard服务: http://localhost:5004")
    app.run(debug=True, port=5004, host='0.0.0.0')
