#!/usr/bin/env python3
"""
数据库初始化脚本
一键创建所有必要的表结构和索引

使用方法:
    python scripts/init_database.py

作者: 系统自动生成
日期: 2026-04-30
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import duckdb


def get_db_path():
    """获取数据库路径"""
    return project_root / 'data' / 'Astock3.duckdb'


def create_database_and_tables():
    """创建数据库和所有表"""
    db_path = get_db_path()
    print(f"📦 创建数据库: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = duckdb.connect(str(db_path))
    cursor = conn.cursor()

    print("🔧 创建所有表...")

    # =========================================================================
    # DWD层数据表（核心数据）
    # =========================================================================

    # 1. dwd_daily_price - 日线行情（最核心表）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_daily_price (
        trade_date DATE,
        ts_code VARCHAR,
        open FLOAT,
        high FLOAT,
        low FLOAT,
        close FLOAT,
        vol BIGINT,
        amount DOUBLE,
        pct_chg DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (trade_date, ts_code)
    );
    """)
    print("   ✓ dwd_daily_price (日线行情)")

    # 2. dwd_daily_basic - 日线基本指标
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_daily_basic (
        trade_date DATE,
        ts_code VARCHAR,
        close DOUBLE,
        pe_ttm DOUBLE,
        pe DOUBLE,
        ps_ttm DOUBLE,
        ps DOUBLE,
        pcf DOUBLE,
        pb DOUBLE,
        total_mv DOUBLE,
        circ_mv DOUBLE,
        amount DOUBLE,
        turn_rate DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (trade_date, ts_code)
    );
    """)
    print("   ✓ dwd_daily_basic (日线基本指标)")

    # 3. dwd_stock_info - 股票基础信息
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_stock_info (
        ts_code VARCHAR PRIMARY KEY,
        symbol VARCHAR,
        name VARCHAR,
        area VARCHAR,
        industry VARCHAR,
        market VARCHAR,
        list_date DATE,
        is_hs VARCHAR,
        act_name VARCHAR,
        data_source VARCHAR DEFAULT 'tushare'
    );
    """)
    print("   ✓ dwd_stock_info (股票基础信息)")

    # 4. dwd_index_daily - 指数日线
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_index_daily (
        index_code VARCHAR,
        trade_date DATE,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        pre_close DOUBLE,
        change DOUBLE,
        pct_change DOUBLE,
        vol BIGINT,
        amount DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (index_code, trade_date)
    );
    """)
    print("   ✓ dwd_index_daily (指数日线)")

    # 5. dwd_trade_calendar - 交易日历
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_trade_calendar (
        trade_date DATE,
        exchange VARCHAR,
        is_open BOOLEAN,
        PRIMARY KEY (trade_date, exchange)
    );
    """)
    print("   ✓ dwd_trade_calendar (交易日历)")

    # 6. dwd_adj_factor - 复权因子
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_adj_factor (
        ts_code VARCHAR,
        trade_date DATE,
        adj_factor DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (ts_code, trade_date)
    );
    """)
    print("   ✓ dwd_adj_factor (复权因子)")

    # 7. dwd_daily_price_qfq - 前复权日线
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_daily_price_qfq (
        ts_code VARCHAR,
        trade_date DATE,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        vol BIGINT,
        amount DOUBLE,
        pct_chg DOUBLE,
        adj_factor DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (trade_date, ts_code)
    );
    """)
    print("   ✓ dwd_daily_price_qfq (前复权日线)")

    # 8. dwd_daily_price_hfq - 后复权日线
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_daily_price_hfq (
        ts_code VARCHAR,
        trade_date DATE,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        vol BIGINT,
        amount DOUBLE,
        pct_chg DOUBLE,
        adj_factor DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (trade_date, ts_code)
    );
    """)
    print("   ✓ dwd_daily_price_hfq (后复权日线)")

    # 9. dwd_income - 利润表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_income (
        ts_code VARCHAR,
        ann_date DATE,
        f_ann_date DATE,
        end_date DATE,
        report_type VARCHAR,
        comp_type VARCHAR,
        basic_eps DOUBLE,
        diluted_eps DOUBLE,
        total_revenue DOUBLE,
        revenue DOUBLE,
        total_profit DOUBLE,
        profit DOUBLE,
        income_tax DOUBLE,
        n_income DOUBLE,
        n_income_attr_p DOUBLE,
        total_cogs DOUBLE,
        operate_profit DOUBLE,
        invest_income DOUBLE,
        non_op_income DOUBLE,
        asset_impair_loss DOUBLE,
        net_profit_with_non_recurring DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (ts_code, ann_date, end_date, report_type)
    );
    """)
    print("   ✓ dwd_income (利润表)")

    # 10. dwd_balancesheet - 资产负债表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_balancesheet (
        ts_code VARCHAR,
        ann_date DATE,
        f_ann_date DATE,
        end_date DATE,
        report_type VARCHAR,
        comp_type VARCHAR,
        total_assets DOUBLE,
        total_liab DOUBLE,
        total_hldr_eqy_excl_min_int DOUBLE,
        hldr_eqy_excl_min_int DOUBLE,
        minority_int DOUBLE,
        total_liab_ht_holder DOUBLE,
        notes_payable DOUBLE,
        accounts_payable DOUBLE,
        advance_receipts DOUBLE,
        total_current_assets DOUBLE,
        total_non_current_assets DOUBLE,
        fixed_assets DOUBLE,
        cip DOUBLE,
        total_current_liab DOUBLE,
        total_non_current_liab DOUBLE,
        lt_borrow DOUBLE,
        bonds_payable DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (ts_code, ann_date, end_date, report_type)
    );
    """)
    print("   ✓ dwd_balancesheet (资产负债表)")

    # 11. dwd_cashflow - 现金流量表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dwd_cashflow (
        ts_code VARCHAR,
        ann_date DATE,
        f_ann_date DATE,
        end_date DATE,
        report_type VARCHAR,
        comp_type VARCHAR,
        net_profit DOUBLE,
        fin_exp DOUBLE,
        c_fr_oper_a DOUBLE,
        c_fr_oper_a_op_ttp DOUBLE,
        c_inf_fr_oper_a DOUBLE,
        c_paid_goods_sold DOUBLE,
        c_paid_to_for_employees DOUBLE,
        c_paid_taxes DOUBLE,
        other_cash_fr_oper_a DOUBLE,
        n_cashflow_act DOUBLE,
        c_fr_oper_b DOUBLE,
        c_fr_inv_a DOUBLE,
        c_to_inv_a DOUBLE,
        c_fr_fin_a DOUBLE,
        c_to_fin_a DOUBLE,
        n_cash_in_fin_a DOUBLE,
        n_cash_in_op_b DOUBLE,
        n_cash_out_inv_b DOUBLE,
        n_cash_out_fin_b DOUBLE,
        n_cash_in_op_c DOUBLE,
        n_cash_out_inv_c DOUBLE,
        n_cash_out_fin_c DOUBLE,
        end_cash DOUBLE,
        cap_crisis_shrg DOUBLE,
        data_source VARCHAR DEFAULT 'tushare',
        PRIMARY KEY (ts_code, ann_date, end_date, report_type)
    );
    """)
    print("   ✓ dwd_cashflow (现金流量表)")

    # =========================================================================
    # 信号系统表
    # =========================================================================

    # 12. daily_signals - 每日信号
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_signals (
        date DATE,
        code VARCHAR,
        name VARCHAR,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        volume BIGINT,
        amount DOUBLE,
        prev_close DOUBLE,
        change_pct DOUBLE,
        涨停价 DOUBLE,
        跌停价 DOUBLE,
        涨停 BOOLEAN,
        跌停 BOOLEAN,
        一字涨停 BOOLEAN,
        score_b1 DOUBLE,
        score_b2 DOUBLE,
        score_blk DOUBLE,
        score_dl DOUBLE,
        score_dz30 DOUBLE,
        score_scb DOUBLE,
        signal_buy_b1 BOOLEAN,
        signal_buy_b2 BOOLEAN,
        signal_buy_blk BOOLEAN,
        signal_buy_dl BOOLEAN,
        signal_buy_dz30 BOOLEAN,
        signal_buy_scb BOOLEAN,
        signal_buy_blkB2 BOOLEAN,
        signal_sell_b1 BOOLEAN,
        signal_sell_b2 BOOLEAN,
        signal_sell_blk BOOLEAN,
        signal_sell_dl BOOLEAN,
        signal_sell_dz30 BOOLEAN,
        signal_sell_scb BOOLEAN,
        signal_sell_blkB2 BOOLEAN,
        score_s1 DOUBLE,
        signal_s1_full BOOLEAN,
        signal_s1_half BOOLEAN,
        signal_跌破多空线 BOOLEAN,
        signal_止损 BOOLEAN,
        indicators JSON,
        PRIMARY KEY (date, code)
    );
    """)
    print("   ✓ daily_signals (每日信号)")

    # 13. positions - 持仓记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY,
        code VARCHAR,
        name VARCHAR,
        strategy VARCHAR,
        buy_date DATE,
        shares INTEGER,
        buy_price DOUBLE,
        buy_change_pct DOUBLE,
        buy_score_b1 DOUBLE,
        buy_score_b2 DOUBLE,
        buy_dif DOUBLE,
        buy_j_value DOUBLE,
        buy_知行短期趋势线 DOUBLE,
        buy_知行多空线 DOUBLE,
        current_price DOUBLE,
        current_score_s1 DOUBLE,
        current_跌破多空线 BOOLEAN,
        stop_loss_pct DOUBLE DEFAULT 0.03,
        status VARCHAR DEFAULT 'holding',
        sell_date DATE,
        sell_price DOUBLE,
        sell_reason VARCHAR,
        profit_loss DOUBLE,
        profit_pct DOUBLE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("   ✓ positions (持仓记录)")

    # =========================================================================
    # 回测系统表
    # =========================================================================

    # 14. backtest_run - 回测运行记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_run (
        run_id VARCHAR PRIMARY KEY,
        strategy_name VARCHAR NOT NULL,
        strategy_params JSON,
        start_date DATE,
        end_date DATE,
        universe VARCHAR,
        benchmark VARCHAR,
        initial_capital FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        status VARCHAR DEFAULT 'running',
        error_message VARCHAR
    );
    """)
    print("   ✓ backtest_run (回测运行)")

    # 15. backtest_trades - 回测交易明细
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_trades (
        id BIGINT,
        run_id VARCHAR,
        date DATE,
        datetime TIMESTAMP,
        code VARCHAR,
        name VARCHAR,
        industry VARCHAR,
        market_cap_group VARCHAR,
        action VARCHAR,
        price FLOAT,
        volume INTEGER,
        amount FLOAT,
        commission FLOAT,
        tax FLOAT,
        total_cost FLOAT,
        signal_type VARCHAR,
        PRIMARY KEY (run_id, id)
    );
    """)
    print("   ✓ backtest_trades (回测交易)")

    # 16. backtest_daily_pnl - 回测每日盈亏
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_daily_pnl (
        run_id VARCHAR,
        date DATE,
        total_value FLOAT,
        cash FLOAT,
        market_value FLOAT,
        daily_pnl FLOAT,
        daily_return FLOAT,
        cumulative_return FLOAT,
        benchmark_return FLOAT,
        excess_return FLOAT,
        drawdown FLOAT,
        positions JSON,
        PRIMARY KEY (run_id, date)
    );
    """)
    print("   ✓ backtest_daily_pnl (回测每日盈亏)")

    # 17. backtest_performance - 回测绩效指标
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS backtest_performance (
        run_id VARCHAR PRIMARY KEY,
        total_return FLOAT,
        annualized_return FLOAT,
        benchmark_return FLOAT,
        excess_return FLOAT,
        volatility FLOAT,
        max_drawdown FLOAT,
        max_drawdown_duration INT,
        var_95 FLOAT,
        sharpe_ratio FLOAT,
        sortino_ratio FLOAT,
        calmar_ratio FLOAT,
        information_ratio FLOAT,
        total_trades INT,
        winning_trades INT,
        losing_trades INT,
        win_rate FLOAT,
        avg_profit FLOAT,
        avg_loss FLOAT,
        profit_loss_ratio FLOAT,
        industry_analysis JSON,
        cap_group_analysis JSON,
        monthly_returns JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("   ✓ backtest_performance (回测绩效)")

    # 18. batch_backtest_results - 批量回测结果
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batch_backtest_results (
        result_id BIGINT,
        batch_id VARCHAR,
        stock_code VARCHAR,
        stock_name VARCHAR,
        status VARCHAR,
        total_return FLOAT,
        annualized_return FLOAT,
        max_drawdown FLOAT,
        sharpe_ratio FLOAT,
        win_rate FLOAT,
        total_trades INTEGER,
        final_value FLOAT,
        initial_cash FLOAT,
        error_message VARCHAR,
        completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (result_id)
    );
    """)
    print("   ✓ batch_backtest_results (批量回测结果)")

    # 19. batch_backtest_daily_pnl - 批量回测每日汇总
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batch_backtest_daily_pnl (
        batch_id VARCHAR,
        date DATE,
        total_value DOUBLE,
        total_pnl DOUBLE,
        total_pnl_pct DOUBLE,
        cumulative_return DOUBLE,
        drawdown DOUBLE,
        positions JSON,
        PRIMARY KEY (batch_id, date)
    );
    """)
    print("   ✓ batch_backtest_daily_pnl (批量回测每日汇总)")

    # 20. batch_backtest_params - 参数扫描结果
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS batch_backtest_params (
        id BIGINT,
        batch_id VARCHAR NOT NULL,
        param_name VARCHAR NOT NULL,
        param_values JSON NOT NULL,
        results JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(batch_id, param_name)
    );
    """)
    print("   ✓ batch_backtest_params (参数扫描)")

    # =========================================================================
    # 投资组合表
    # =========================================================================

    # 21. portfolio_daily - 每日组合状态
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_daily (
        id INTEGER PRIMARY KEY,
        date DATE NOT NULL UNIQUE,
        init_cash DECIMAL(12,2) NOT NULL,
        position_cost DECIMAL(12,2) NOT NULL,
        position_value DECIMAL(12,2) NOT NULL,
        position_pnl DECIMAL(12,2) NOT NULL,
        closed_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
        total_pnl DECIMAL(12,2) NOT NULL,
        available_cash DECIMAL(12,2) NOT NULL,
        position_ratio DECIMAL(5,2) NOT NULL,
        notes VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_portfolio_date ON portfolio_daily(date);
    """)
    print("   ✓ portfolio_daily (每日组合)")

    # 22. portfolio_daily_strategy - 分策略每日状态
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_daily_strategy (
        id INTEGER,
        date DATE,
        strategy VARCHAR,
        position_cost DECIMAL(12,2),
        position_value DECIMAL(12,2),
        position_pnl DECIMAL(12,2),
        closed_pnl DECIMAL(12,2),
        total_pnl DECIMAL(12,2),
        trade_count INTEGER,
        notes VARCHAR,
        created_at TIMESTAMP
    );
    """)
    print("   ✓ portfolio_daily_strategy (分策略组合)")

    # =========================================================================
    # 数据流水线表
    # =========================================================================

    # 23. data_pipeline_run - 流水线运行记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_pipeline_run (
        id INTEGER PRIMARY KEY,
        pipeline_id VARCHAR,
        pipeline_name VARCHAR,
        step_name VARCHAR,
        step_order INT,
        created_at TIMESTAMP,
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        duration_sec FLOAT,
        params JSON,
        status VARCHAR,
        records_count INT,
        error_message TEXT,
        depends_on VARCHAR,
        dependency_met BOOLEAN,
        UNIQUE(pipeline_id, step_name)
    );
    """)
    print("   ✓ data_pipeline_run (流水线运行)")

    # 24. step_update_log - 步骤更新日志
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS step_update_log (
        id INTEGER PRIMARY KEY,
        pipeline_id VARCHAR,
        step_name VARCHAR,
        update_type VARCHAR,
        update_time TIMESTAMP,
        start_time TIMESTAMP,
        end_time TIMESTAMP,
        duration_sec FLOAT,
        expected_count INT,
        actual_count INT,
        is_success BOOLEAN,
        error_message TEXT,
        error_details JSON,
        step_details JSON,
        validation_results JSON,
        check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("   ✓ step_update_log (更新日志)")

    # =========================================================================
    # 运营监控表
    # =========================================================================

    # 25. agent_analysis_results - Agent分析结果
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_analysis_results (
        run_id VARCHAR,
        symbol VARCHAR,
        trade_date VARCHAR,
        result_json VARCHAR,
        created_at TIMESTAMP
    );
    """)
    print("   ✓ agent_analysis_results (Agent分析结果)")

    # 26. pipeline_monitor_flag - 流水线监控标记
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pipeline_monitor_flag (
        id INTEGER,
        date VARCHAR,
        completed BOOLEAN,
        completed_at TIMESTAMP
    );
    """)
    print("   ✓ pipeline_monitor_flag (监控标记)")

    # 27. trade_audit_log - 交易审计日志
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_audit_log (
        id INTEGER,
        audit_date DATE,
        check_item VARCHAR,
        check_type VARCHAR,
        severity VARCHAR,
        status VARCHAR,
        detail VARCHAR,
        fix_action VARCHAR,
        before_val VARCHAR,
        after_val VARCHAR,
        auditor VARCHAR,
        created_at TIMESTAMP
    );
    """)
    print("   ✓ trade_audit_log (交易审计)")

    # =========================================================================
    # 策略注册表
    # =========================================================================

    # 28. strategy_registry - 策略注册表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_registry (
        id VARCHAR PRIMARY KEY,
        name VARCHAR NOT NULL UNIQUE,
        display_name VARCHAR,
        class_path VARCHAR NOT NULL,
        source_file VARCHAR,
        description TEXT,
        version VARCHAR DEFAULT '1.0.0',
        author VARCHAR,
        status VARCHAR DEFAULT 'active',
        strategy_type VARCHAR,
        threshold_required BOOLEAN DEFAULT FALSE,
        min_data_days INT DEFAULT 0,
        param_schema JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("   ✓ strategy_registry (策略注册)")

    # 29. strategy_metadata - 策略元数据
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_metadata (
        name VARCHAR PRIMARY KEY,
        signal_abbrev VARCHAR,
        class_name VARCHAR,
        description VARCHAR,
        status VARCHAR DEFAULT 'draft',
        current_version VARCHAR,
        promotion_config JSON,
        latest_backtest JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("   ✓ strategy_metadata (策略元数据)")

    # 30. strategy_versions - 策略版本历史
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_versions (
        id INTEGER PRIMARY KEY,
        strategy_name VARCHAR NOT NULL,
        signal_abbrev VARCHAR,
        version VARCHAR NOT NULL,
        backtest_metrics JSON,
        backtest_params JSON,
        run_id VARCHAR,
        status VARCHAR DEFAULT 'tested',
        promoted_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(strategy_name, version)
    );
    """)
    print("   ✓ strategy_versions (策略版本)")

    # 31. strategy_params - 策略参数
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_params (
        id INTEGER PRIMARY KEY,
        strategy_name VARCHAR NOT NULL,
        param_name VARCHAR NOT NULL,
        param_type VARCHAR,
        default_value JSON,
        current_value JSON,
        description TEXT,
        constraints JSON,
        is_required BOOLEAN DEFAULT FALSE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(strategy_name, param_name)
    );
    """)
    print("   ✓ strategy_params (策略参数)")

    # 32. strategy_params_history - 参数修改历史
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_params_history (
        id INTEGER PRIMARY KEY,
        strategy_name VARCHAR NOT NULL,
        param_name VARCHAR NOT NULL,
        old_value JSON,
        new_value JSON,
        changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        changed_by VARCHAR
    );
    """)
    print("   ✓ strategy_params_history (参数历史)")

    # 33. signal_events - 信号事件记录
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS signal_events (
        id BIGINT PRIMARY KEY,
        date DATE,
        code VARCHAR,
        name VARCHAR,
        signal_abbrev VARCHAR,
        version VARCHAR,
        signal_type VARCHAR,
        score DOUBLE,
        signal_field VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    print("   ✓ signal_events (信号事件)")

    # =========================================================================
    # 因子数据表
    # =========================================================================

    # 34. factor_data - 多因子数据
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factor_data (
        date DATE,
        code VARCHAR,
        pe_ttm FLOAT,
        pb FLOAT,
        ps_ttm FLOAT,
        pcf_ttm FLOAT,
        dividend_yield FLOAT,
        roe FLOAT,
        roa FLOAT,
        gross_margin FLOAT,
        net_margin FLOAT,
        debt_to_asset FLOAT,
        revenue_growth_yoy FLOAT,
        profit_growth_yoy FLOAT,
        revenue_growth_qoq FLOAT,
        profit_growth_qoq FLOAT,
        macd_dif FLOAT,
        macd_dea FLOAT,
        macd_histogram FLOAT,
        kdj_k FLOAT,
        kdj_d FLOAT,
        kdj_j FLOAT,
        rsi_6 FLOAT,
        rsi_12 FLOAT,
        rsi_24 FLOAT,
        boll_upper FLOAT,
        boll_mid FLOAT,
        boll_lower FLOAT,
        ma_5 FLOAT,
        ma_10 FLOAT,
        ma_20 FLOAT,
        ma_60 FLOAT,
        volatility_20d FLOAT,
        turnover_20d FLOAT,
        volume_ratio FLOAT,
        price_momentum_20d FLOAT,
        price_momentum_60d FLOAT,
        custom_factor_1 FLOAT,
        custom_factor_2 FLOAT,
        custom_factor_3 FLOAT,
        custom_factor_4 FLOAT,
        custom_factor_5 FLOAT,
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (date, code)
    );
    """)
    print("   ✓ factor_data (因子数据)")

    # 35. factor_ic - 因子IC分析
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factor_ic (
        date DATE,
        factor_name VARCHAR,
        ic FLOAT,
        ic_rank FLOAT,
        ir FLOAT,
        ic_positive_ratio FLOAT,
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (date, factor_name)
    );
    """)
    print("   ✓ factor_ic (因子IC)")

    # 36. factor_return - 因子收益分析
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factor_return (
        date DATE,
        factor_name VARCHAR,
        long_return FLOAT,
        short_return FLOAT,
        long_short_return FLOAT,
        quantile_returns JSON,
        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (date, factor_name)
    );
    """)
    print("   ✓ factor_return (因子收益)")

    # =========================================================================
    # VIEW层（向后兼容）
    # =========================================================================

    # 37. stock_info 视图
    cursor.execute("""
    CREATE OR REPLACE VIEW stock_info AS
    SELECT
        ts_code AS code,
        symbol,
        name,
        area,
        industry,
        market,
        list_date AS listing_date,
        is_hs,
        act_name AS act_name,
        data_source
    FROM dwd_stock_info;
    """)
    print("   ✓ stock_info (视图)")

    # 38. daily_basic 视图
    cursor.execute("""
    CREATE OR REPLACE VIEW daily_basic AS
    SELECT
        trade_date,
        ts_code,
        close,
        pe_ttm,
        pe,
        ps_ttm,
        ps,
        pcf,
        pb,
        total_mv,
        circ_mv,
        amount,
        turn_rate,
        data_source
    FROM dwd_daily_basic;
    """)
    print("   ✓ daily_basic (视图)")

    # 39. index_daily 视图
    cursor.execute("""
    CREATE OR REPLACE VIEW index_daily AS
    SELECT
        trade_date,
        index_code AS ts_code,
        open,
        high,
        low,
        close,
        vol,
        amount,
        pct_change,
        data_source
    FROM dwd_index_daily;
    """)
    print("   ✓ index_daily (视图)")

    # 40. v_position_analysis 视图
    cursor.execute("""
    CREATE OR REPLACE VIEW v_position_analysis AS
    SELECT
        p.*,
        s.industry,
        d.pe AS buy_pe,
        d.pb AS buy_pb,
        d.turn_rate AS buy_turnover_rate
    FROM positions p
    LEFT JOIN dwd_stock_info s ON p.code = s.symbol
    LEFT JOIN daily_basic d ON p.code = d.ts_code AND d.trade_date = p.buy_date
    WHERE p.status = 'sold';
    """)
    print("   ✓ v_position_analysis (视图)")

    conn.commit()

    # =========================================================================
    # 验证结果
    # =========================================================================

    # 验证表创建
    tables = cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """).fetchall()

    print(f"\n{'='*60}")
    print(f"✅ 成功创建 {len(tables)} 个数据表")

    # 验证视图创建
    views = cursor.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'main' AND table_type = 'VIEW'
        ORDER BY table_name
    """).fetchall()

    print(f"✅ 成功创建 {len(views)} 个视图")
    print(f"{'='*60}")

    conn.close()

    print(f"\n🎉 数据库初始化完成！")
    print(f"📁 数据库路径: {db_path}")
    print(f"\n📋 下一步操作:")
    print(f"   1. 下载股票列表: python data/updaters/fetcher_all_stockV3.py")
    print(f"   2. 下载日线数据: python data/updaters/fetcher_daily_priceV4.py --start-date 20250101")
    print(f"   3. 运行信号扫描: python signals/scan_signals_v2.py --date 20260429 --workers 10")

    return True


def verify_database():
    """验证数据库"""
    db_path = get_db_path()
    if not db_path.exists():
        print(f"❌ 数据库不存在: {db_path}")
        return False

    print(f"\n🔍 验证数据库...")

    conn = duckdb.connect(str(db_path), read_only=True)

    # 检查核心表
    core_tables = [
        'dwd_daily_price',
        'dwd_daily_basic',
        'dwd_stock_info',
        'daily_signals',
        'positions',
        'backtest_run'
    ]

    all_ok = True
    for table in core_tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"   ✓ {table}: {count:,} 条记录")
        except Exception as e:
            print(f"   ✗ {table}: {str(e)}")
            all_ok = False

    # 检查最新数据日期
    try:
        latest = conn.execute("SELECT MAX(trade_date) FROM dwd_daily_price").fetchone()[0]
        print(f"\n📅 最新日线数据日期: {latest}")
    except:
        print(f"\n📅 日线数据尚未下载")

    conn.close()

    if all_ok:
        print(f"\n✅ 数据库验证通过！")
    else:
        print(f"\n⚠️ 数据库验证有问题，请检查错误")

    return all_ok


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='数据库初始化脚本')
    parser.add_argument('--verify', action='store_true', help='仅验证数据库')
    parser.add_argument('--force', action='store_true', help='强制重建（删除旧数据库）')
    args = parser.parse_args()

    if args.verify:
        verify_database()
    else:
        if args.force:
            db_path = get_db_path()
            if db_path.exists():
                print(f"⚠️ 删除旧数据库: {db_path}")
                db_path.unlink()

        create_database_and_tables()
        verify_database()
