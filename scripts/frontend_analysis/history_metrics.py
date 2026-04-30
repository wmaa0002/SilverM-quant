"""
历史交易综合分析计算引擎
独立脚本，计算所有绩效指标供前端展示
"""
import sys
import os
import json
from pathlib import Path

import duckdb
import pandas as pd
import numpy as np

DB_PATH = Path(__file__).parent.parent.parent / 'data' / 'Astock3.duckdb'


def get_db():
    return duckdb.connect(str(DB_PATH))


def safe_round(value, decimals=2):
    if value is None:
        return None
    try:
        if np.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    return round(value, decimals)


def map_sell_reason(reason):
    if not reason:
        return '信号卖出'
    
    reason_map = {
        'take_profit': '止盈卖出',
        'stop_loss': '止损卖出',
        'signal': '信号卖出',
        'rebalance': '调仓卖出',
    }
    
    reason_str = str(reason).lower()
    for key, value in reason_map.items():
        if key in reason_str:
            return value
    
    return f'信号卖出({reason})'


def get_empty_summary():
    return {
        'total_trades': 0, 'total_profit': 0, 'win_rate': 0,
        'avg_holding_days': 0, 'annualized_return': 0,
        'cumulative_return': 0, 'volatility': 0,
        'sharpe_ratio': 0, 'sortino_ratio': 0,
        'max_drawdown': 0, 'max_drawdown_duration': 0,
        'calmar_ratio': 0, 'profit_loss_ratio': 0,
        'expectancy': 0, 'best_trade': 0, 'worst_trade': 0,
        'avg_profit': 0, 'avg_loss': 0, 'avg_drawdown': 0
    }


def get_empty_metrics():
    return {
        'summary': get_empty_summary(),
        'by_signal_type': [], 'by_industry': [], 'by_market_cap': [],
        'holding_period_distribution': {}, 'monthly_returns': []
    }


def code_to_ts_code(code: str) -> str:
    if not code:
        return code
    if '.' in code:
        return code
    if code.startswith('6'):
        return f"{code}.SH"
    else:
        return f"{code}.SZ"


def get_cap_group(total_mv: float) -> tuple:
    if total_mv is None or total_mv <= 0:
        return ('unknown', '未知', 0)
    if total_mv > 20000000:
        return ('2000亿以上', '2000亿以上', 1)
    elif total_mv > 10000000:
        return ('1000亿-2000亿', '1000亿-2000亿', 2)
    elif total_mv > 5000000:
        return ('500亿-1000亿', '500亿-1000亿', 3)
    elif total_mv > 3000000:
        return ('300亿-500亿', '300亿-500亿', 4)
    elif total_mv > 1000000:
        return ('100亿-300亿', '100亿-300亿', 5)
    elif total_mv > 500000:
        return ('50亿-100亿', '50亿-100亿', 6)
    else:
        return ('50亿以下', '50亿以下', 7)


def calculate_all_metrics():
    """
    综合分析历史交易数据
    
    数据来源表:
    1. portfolio_daily - 净值曲线数据
       字段: date, init_cash, total_value
       用途: 计算年化收益率、波动率、夏普比率等
    
    2. v_position_analysis - 历史交易视图
       视图定义: positions LEFT JOIN dwd_stock_info LEFT JOIN dwd_daily_basic
       字段: code, name, buy_date, sell_date, profit_loss, buy_price, shares, stop_loss_pct, industry
       用途: 交易统计、市值分组分析
    
    3. dwd_daily_basic - 每日指标表
       字段: ts_code, trade_date, total_mv
       用途: 市值分组分析 (根据买入日期匹配)
    """
    db = get_db()
    
    try:
        equity_df = db.execute("""
            SELECT date, init_cash, total_value
            FROM portfolio_daily
            ORDER BY date
        """).df()
        
        if len(equity_df) == 0:
            return get_empty_metrics()
        
        init_cash = float(equity_df['init_cash'].iloc[0])
        equity_df['daily_return'] = equity_df['total_value'].pct_change()
        
        final_value = float(equity_df['total_value'].iloc[-1])
        cumulative_return = (final_value - init_cash) / init_cash * 100
        
        trading_days = len(equity_df)
        
        if trading_days > 0 and init_cash > 0:
            annualized_return = ((final_value / init_cash) ** (252 / trading_days) - 1) * 100
        else:
            annualized_return = 0
        
        daily_returns = equity_df['daily_return'].dropna().values
        
        volatility = np.std(daily_returns) * np.sqrt(252) * 100 if len(daily_returns) > 0 else 0
        
        risk_free_rate = 0.03
        if volatility > 0:
            sharpe = (annualized_return / 100 - risk_free_rate) / (volatility / 100)
        else:
            sharpe = 0
        
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0
        if downside_std > 0:
            sortino = (annualized_return / 100 - risk_free_rate) / (downside_std * np.sqrt(252))
        else:
            sortino = 0
        
        peak_value = init_cash
        max_drawdown = 0
        max_drawdown_duration = 0
        current_dd_duration = 0
        all_drawdowns = []
        
        for i in range(len(equity_df)):
            current_value = float(equity_df['total_value'].iloc[i])
            if current_value > peak_value:
                peak_value = current_value
                current_dd_duration = 0
            else:
                current_dd_duration += 1
                drawdown = (peak_value - current_value) / peak_value * 100
                all_drawdowns.append(drawdown)
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_duration = current_dd_duration
        
        avg_drawdown = -sum(all_drawdowns) / len(all_drawdowns) if len(all_drawdowns) > 0 else 0
        calmar = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        trades_df = db.execute("""
            SELECT code, name, strategy, buy_date, sell_date,
                   profit_loss, profit_pct, industry, buy_price, shares, stop_loss_pct
            FROM v_position_analysis
            ORDER BY sell_date DESC
        """).df()
        
        total_trades = len(trades_df)
        if total_trades == 0:
            return {
                'summary': get_empty_summary(),
                'by_signal_type': [], 'by_industry': [], 'by_market_cap': [],
                'holding_period_distribution': {}, 'monthly_returns': []
            }
        
        trades_df['buy_date'] = pd.to_datetime(trades_df['buy_date'])
        trades_df['sell_date'] = pd.to_datetime(trades_df['sell_date'])
        trades_df['holding_days'] = (trades_df['sell_date'] - trades_df['buy_date']).dt.days
        trades_df['buy_signal_type'] = trades_df['strategy'].apply(lambda x: x if x else '趋势择时')
        
        unique_trades = trades_df[['code', 'buy_date']].drop_duplicates()
        code_to_mv = {}
        for _, row in unique_trades.iterrows():
            ts_code = code_to_ts_code(row['code'])
            buy_date = row['buy_date'].strftime('%Y-%m-%d') if hasattr(row['buy_date'], 'strftime') else str(row['buy_date'])
            query = f"SELECT total_mv FROM dwd_daily_basic WHERE ts_code = '{ts_code}' AND trade_date = '{buy_date}'"
            result = db.execute(query).fetchone()
            if result and result[0]:
                code_to_mv[(row['code'], buy_date)] = result[0]
        
        def get_market_cap(row):
            key = (row['code'], row['buy_date'].strftime('%Y-%m-%d') if hasattr(row['buy_date'], 'strftime') else str(row['buy_date']))
            return code_to_mv.get(key)
        
        trades_df['market_cap'] = trades_df.apply(get_market_cap, axis=1)
        trades_df['market_cap_group'] = trades_df['market_cap'].apply(lambda x: get_cap_group(x) if pd.notna(x) else ('unknown', '未知', 0))
        
        total_profit = trades_df['profit_loss'].sum()
        win_count = len(trades_df[trades_df['profit_loss'] > 0])
        win_rate = win_count / total_trades * 100 if total_trades > 0 else 0
        avg_holding_days = trades_df['holding_days'].mean()
        
        profits = trades_df[trades_df['profit_loss'] > 0]['profit_loss']
        losses = trades_df[trades_df['profit_loss'] < 0]['profit_loss']
        profit_loss_ratio = abs(profits.mean() / losses.mean()) if len(losses) > 0 and losses.mean() != 0 else 0
        expectancy = trades_df['profit_loss'].mean()
        best_trade = trades_df['profit_loss'].max()
        worst_trade = trades_df['profit_loss'].min()
        avg_profit = profits.mean() if len(profits) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        
        trades_df['risk_amount'] = trades_df['buy_price'] * trades_df['shares'] * trades_df['stop_loss_pct']
        trades_df['profit_r'] = trades_df['profit_loss'] / trades_df['risk_amount']
        avg_profit_r = trades_df[trades_df['profit_loss'] > 0]['profit_r'].mean() if len(trades_df[trades_df['profit_loss'] > 0]) > 0 else 0
        avg_loss_r = trades_df[trades_df['profit_loss'] < 0]['profit_r'].mean() if len(trades_df[trades_df['profit_loss'] < 0]) > 0 else 0
        win_rate_decimal = win_count / total_trades if total_trades > 0 else 0
        loss_rate_decimal = 1 - win_rate_decimal
        expectancy_r = (win_rate_decimal * avg_profit_r) - (loss_rate_decimal * 1) if total_trades > 0 else 0
        
        summary = {
            'total_trades': total_trades,
            'total_profit': safe_round(total_profit, 2),
            'win_rate': safe_round(win_rate, 2),
            'avg_holding_days': safe_round(avg_holding_days, 1),
            'annualized_return': safe_round(annualized_return, 2),
            'cumulative_return': safe_round(cumulative_return, 2),
            'volatility': safe_round(volatility, 2),
            'sharpe_ratio': safe_round(sharpe, 2),
            'sortino_ratio': safe_round(sortino, 2),
            'max_drawdown': safe_round(-max_drawdown, 2),
            'max_drawdown_duration': max_drawdown_duration,
            'calmar_ratio': safe_round(calmar, 2),
            'profit_loss_ratio': safe_round(profit_loss_ratio, 2),
            'expectancy': safe_round(expectancy, 2),
            'expectancy_r': safe_round(expectancy_r, 3),
            'best_trade': safe_round(best_trade, 2),
            'worst_trade': safe_round(worst_trade, 2),
            'avg_profit': safe_round(avg_profit, 2),
            'avg_loss': safe_round(avg_loss, 2),
            'avg_drawdown': safe_round(avg_drawdown, 2) if trading_days > 0 else 0
        }
        
        signal_analysis = []
        for signal_type in trades_df['buy_signal_type'].unique():
            signal_df = trades_df[trades_df['buy_signal_type'] == signal_type]
            if len(signal_df) > 0:
                signal_analysis.append({
                    'signal_name': signal_type, 'signal_type': 'buy',
                    'trade_count': len(signal_df),
                    'win_count': len(signal_df[signal_df['profit_loss'] > 0]),
                    'win_rate': safe_round(len(signal_df[signal_df['profit_loss'] > 0]) / len(signal_df) * 100, 2),
                    'total_profit': safe_round(signal_df['profit_loss'].sum(), 2),
                    'avg_profit_per_trade': safe_round(signal_df['profit_loss'].mean(), 2),
                    'avg_holding_days': safe_round(signal_df['holding_days'].mean(), 1)
                })
        signal_analysis = sorted(signal_analysis, key=lambda x: x['trade_count'], reverse=True)
        
        industry_analysis = []
        for industry in trades_df['industry'].dropna().unique():
            industry_df = trades_df[trades_df['industry'] == industry]
            if len(industry_df) > 0:
                industry_analysis.append({
                    'industry': industry, 'trade_count': len(industry_df),
                    'win_count': len(industry_df[industry_df['profit_loss'] > 0]),
                    'win_rate': safe_round(len(industry_df[industry_df['profit_loss'] > 0]) / len(industry_df) * 100, 2),
                    'total_profit': safe_round(industry_df['profit_loss'].sum(), 2),
                    'avg_holding_days': safe_round(industry_df['holding_days'].mean(), 1)
                })
        industry_analysis = sorted(industry_analysis, key=lambda x: x['trade_count'], reverse=True)[:10]
        
        market_cap_analysis = []
        has_market_cap_data = (
            'market_cap_group' in trades_df.columns and
            trades_df['market_cap_group'].notna().any()
        )
        if has_market_cap_data:
            for cap_group in trades_df['market_cap_group'].dropna().unique():
                cap_df = trades_df[trades_df['market_cap_group'] == cap_group]
                if len(cap_df) > 0:
                    market_cap_analysis.append({
                        'group': cap_group[1] if isinstance(cap_group, tuple) else cap_group,
                        'group_code': cap_group[0] if isinstance(cap_group, tuple) else cap_group,
                        'sort_order': cap_group[2] if isinstance(cap_group, tuple) else 0,
                        'trade_count': len(cap_df),
                        'win_count': len(cap_df[cap_df['profit_loss'] > 0]),
                        'win_rate': safe_round(len(cap_df[cap_df['profit_loss'] > 0]) / len(cap_df) * 100, 2),
                        'total_profit': safe_round(cap_df['profit_loss'].sum(), 2)
                    })
            market_cap_analysis = sorted(market_cap_analysis, key=lambda x: x['sort_order'])
        
        holding_period_distribution = {
            '0-5天': len(trades_df[trades_df['holding_days'] <= 5]),
            '6-10天': len(trades_df[(trades_df['holding_days'] > 5) & (trades_df['holding_days'] <= 10)]),
            '11-20天': len(trades_df[(trades_df['holding_days'] > 10) & (trades_df['holding_days'] <= 20)]),
            '21-30天': len(trades_df[(trades_df['holding_days'] > 20) & (trades_df['holding_days'] <= 30)]),
            '30天以上': len(trades_df[trades_df['holding_days'] > 30])
        }
        
        equity_df['month'] = equity_df['date'].dt.to_period('M')
        monthly_returns = []
        for month in sorted(equity_df['month'].unique()):
            month_df = equity_df[equity_df['month'] == month]
            if len(month_df) > 1:
                month_return = (month_df['total_value'].iloc[-1] - month_df['total_value'].iloc[0]) / month_df['total_value'].iloc[0] * 100
                sell_in_month = trades_df[trades_df['sell_date'].dt.to_period('M') == month]
                monthly_returns.append({
                    'month': str(month),
                    'trade_count': len(sell_in_month),
                    'profit': safe_round(month_return, 2),
                    'profit_value': safe_round(float(month_df['total_value'].iloc[-1] - month_df['total_value'].iloc[0]), 2),
                    'win_rate': safe_round(len(sell_in_month[sell_in_month['profit_loss'] > 0]) / max(1, len(sell_in_month)) * 100, 2)
                })
        
        return {
            'summary': summary,
            'by_signal_type': signal_analysis,
            'by_industry': industry_analysis,
            'by_market_cap': market_cap_analysis,
            'holding_period_distribution': holding_period_distribution,
            'monthly_returns': monthly_returns
        }
    
    finally:
        db.close()


def main():
    metrics = calculate_all_metrics()
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
