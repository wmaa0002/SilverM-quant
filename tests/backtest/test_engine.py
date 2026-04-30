"""
Unit tests for BacktestEngine.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import pandas as pd
import tempfile


class TestBacktestEngineInit:
    """Test cases for BacktestEngine initialization."""

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_init_default(self, mock_cerebro, mock_db_manager):
        """Test default initialization without parameters."""
        from backtest.engine import BacktestEngine
        
        engine = BacktestEngine()
        
        assert engine.initial_cash == 100000.0
        assert engine.commission == 0.0003
        assert engine.stamp_duty == 0.001
        assert engine.slip_page == 0.001
        assert engine.start_date is None
        assert engine.end_date is None
        assert engine._stock_list is None
        mock_cerebro.return_value.broker.setcash.assert_called_once_with(100000.0)
        mock_cerebro.return_value.broker.setcommission.assert_called_once_with(commission=0.0003)
        mock_cerebro.return_value.broker.set_slippage_perc.assert_called_once_with(0.001)

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_init_with_dates(self, mock_cerebro, mock_db_manager):
        """Test initialization with date parameters."""
        from backtest.engine import BacktestEngine
        
        engine = BacktestEngine(
            start_date='20240101',
            end_date='20240331'
        )
        
        assert engine.start_date == '20240101'
        assert engine.end_date == '20240331'
        assert engine._stock_list is None

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_init_with_stock_list(self, mock_cerebro, mock_db_manager):
        """Test initialization with stock list."""
        from backtest.engine import BacktestEngine
        
        stock_list = ['000001', '000002', '600000']
        engine = BacktestEngine(stock_list=stock_list)
        
        assert engine._stock_list == stock_list
        assert engine.get_stock_list() == stock_list

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_init_with_stock_file(self, mock_cerebro, mock_db_manager):
        """Test initialization loading stock list from file."""
        from backtest.engine import BacktestEngine
        
        # Create a temporary file with stock codes
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('000001\n')
            f.write('000002\n')
            f.write('600000\n')
            temp_path = f.name
        
        try:
            engine = BacktestEngine(stock_file=temp_path)
            assert engine._stock_list == ['000001', '000002', '600000']
            assert engine.get_stock_list() == ['000001', '000002', '600000']
        finally:
            Path(temp_path).unlink()

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_init_with_stock_file_not_found(self, mock_cerebro, mock_db_manager):
        """Test initialization with non-existent stock file raises error."""
        from backtest.engine import BacktestEngine
        
        with pytest.raises(FileNotFoundError):
            BacktestEngine(stock_file='/nonexistent/path/stocks.txt')


class TestBacktestEngineRun:
    """Test cases for BacktestEngine run method."""

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_run_returns_metrics(self, mock_cerebro, mock_db_manager):
        """Test run() returns PerformanceMetrics."""
        from backtest.engine import BacktestEngine, PerformanceMetrics
        
        # Setup mock cerebro and strategy
        mock_cerebro_instance = MagicMock()
        mock_cerebro.return_value = mock_cerebro_instance
        
        mock_strategy = MagicMock()
        mock_strategy.analyzers.timereturn.get_analysis.return_value = {}
        mock_strategy.analyzers.returns.get_analysis.return_value = {'rtot': 0.15, 'rnorm': 0.12}
        mock_strategy.analyzers.sharpe.get_analysis.return_value = {'sharperatio': 1.5}
        mock_strategy.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 0.08, 'len': 30}}
        mock_strategy.analyzers.trades.get_analysis.return_value = {
            'total': {'total': 10},
            'won': {'total': 6, 'pnl': {'average': 100}},
            'lost': {'total': 4, 'pnl': {'average': 50}}
        }
        
        mock_cerebro_instance.run.return_value = [mock_strategy]
        mock_cerebro_instance.broker.getvalue.return_value = 115000.0
        
        engine = BacktestEngine(initial_cash=100000.0)
        result = engine.run(save_results=False)
        
        assert 'performance_metrics' in result
        assert isinstance(result['performance_metrics'], PerformanceMetrics)
        metrics = result['performance_metrics']
        assert metrics.total_return == pytest.approx(0.15, rel=1e-2)
        assert metrics.sharpe_ratio == pytest.approx(1.5, rel=1e-2)
        assert metrics.total_trades == 10

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_run_backward_compat(self, mock_cerebro, mock_db_manager):
        """Test run() returns dict with backward compatible fields."""
        from backtest.engine import BacktestEngine
        
        # Setup mock
        mock_cerebro_instance = MagicMock()
        mock_cerebro.return_value = mock_cerebro_instance
        
        mock_strategy = MagicMock()
        mock_strategy.analyzers.timereturn.get_analysis.return_value = {}
        mock_strategy.analyzers.returns.get_analysis.return_value = {'rtot': 0.10, 'rnorm': 0.08}
        mock_strategy.analyzers.sharpe.get_analysis.return_value = {'sharperatio': 1.2}
        mock_strategy.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 0.05, 'len': 20}}
        mock_strategy.analyzers.trades.get_analysis.return_value = {
            'total': {'total': 5},
            'won': {'total': 3, 'pnl': {'average': 80}},
            'lost': {'total': 2, 'pnl': {'average': 40}}
        }
        
        mock_cerebro_instance.run.return_value = [mock_strategy]
        mock_cerebro_instance.broker.getvalue.return_value = 110000.0
        
        engine = BacktestEngine(initial_cash=100000.0)
        result = engine.run(save_results=False)
        
        # Check backward compatible fields
        assert 'total_return' in result
        assert 'metrics' in result
        assert 'final_value' in result
        assert 'initial_value' in result
        assert 'daily_pnl' in result
        assert 'trades' in result
        
        # Check metrics dict contains expected keys
        assert 'total_return' in result['metrics']
        assert 'annualized_return' in result['metrics']
        assert 'sharpe_ratio' in result['metrics']
        assert 'max_drawdown' in result['metrics']
        assert 'total_trades' in result['metrics']
        assert 'win_rate' in result['metrics']


class TestBacktestEngineInvalidStock:
    """Test cases for invalid stock handling."""

    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_with_invalid_stock(self, mock_cerebro, mock_db_manager):
        """Test invalid stock code handling."""
        from backtest.engine import BacktestEngine
        
        # Create engine with stock list containing invalid stock
        engine = BacktestEngine(stock_list=['INVALID', '000001'])
        
        # add_data_from_db should skip stocks not in stock_list
        mock_db_instance = MagicMock()
        mock_db_manager.return_value = mock_db_instance
        mock_db_instance.get_daily_price.return_value = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5),
            'open': [10.0]*5,
            'high': [11.0]*5,
            'low': [9.0]*5,
            'close': [10.5]*5,
            'volume': [1000000]*5
        })
        
        # Should not raise, just skip invalid stock
        # The stock INVALID is not in the database so it will raise ValueError
        mock_db_instance.get_daily_price.side_effect = ValueError("数据库中没有 INVALID 的数据")
        
        # This should raise the error from db
        with pytest.raises(ValueError, match="数据库中没有 INVALID 的数据"):
            engine.add_data_from_db('INVALID')
    
    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_stock_filter_works(self, mock_cerebro, mock_db_manager):
        """Test that stock list filter actually filters stocks."""
        from backtest.engine import BacktestEngine
        
        mock_db_instance = MagicMock()
        mock_db_manager.return_value = mock_db_instance
        
        valid_df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=5),
            'open': [10.0]*5,
            'high': [11.0]*5,
            'low': [9.0]*5,
            'close': [10.5]*5,
            'volume': [1000000]*5
        })
        mock_db_instance.get_daily_price.return_value = valid_df
        
        engine = BacktestEngine(stock_list=['000001', '000002'])
        
        engine.add_data_from_db('000001')
        
        mock_db_instance.get_daily_price.assert_called()
    
    @patch('backtest.engine.DatabaseManager')
    @patch('backtest.engine.bt.Cerebro')
    def test_engine_stock_filter_skips(self, mock_cerebro, mock_db_manager):
        """Test that stocks not in stock_list are skipped."""
        from backtest.engine import BacktestEngine
        
        engine = BacktestEngine(stock_list=['000001'])
        
        mock_db_instance = MagicMock()
        mock_db_manager.return_value = mock_db_instance
        
        # add_data_from_db should return early when stock not in list
        engine.add_data_from_db('000002')  # Not in the list
        
        # get_daily_price should NOT be called since stock is filtered
        mock_db_instance.get_daily_price.assert_not_called()