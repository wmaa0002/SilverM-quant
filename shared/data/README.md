# 统一数据接口

为信号系统和回测系统提供统一的数据获取和指标计算接口。

## 架构设计

```
shared/data/
├── __init__.py                  # 模块导出
├── base_data_provider.py        # 数据提供者基类（抽象接口）
├── signal_data_adapter.py       # 信号系统数据适配器
├── backtest_data_adapter.py     # 回测系统数据适配器
├── indicators_calculator.py      # 统一指标计算器
└── usage_examples.py           # 使用示例和迁移指南
```

## 核心组件

### 1. BaseDataProvider（基类）

定义统一的数据接口规范：
- `get_stock_data()` - 获取股票历史数据
- `get_stock_info()` - 获取股票基础信息
- `get_stock_list()` - 获取股票列表
- `get_positions()` - 获取持仓信息
- `code_to_ts_code()` / `ts_code_to_code()` - 代码格式转换

### 2. SignalDataAdapter（信号系统适配器）

特点：
- 直接从数据库查询数据
- 计算并返回 `indicators` 字典
- 支持持仓信息查询和更新
- 提供 `get_stock_data_by_trading_date()` 方法用于信号扫描

使用示例：
```python
from shared.data import SignalDataAdapter

data_adapter = SignalDataAdapter()

# 获取股票数据
df = data_adapter.get_stock_data_by_trading_date('600000', '2026-04-17', days=150)

# 计算指标
indicators = data_adapter.calculate_indicators(df, '600000')

# 获取持仓信息
positions = data_adapter.get_positions()

# 更新观察状态
data_adapter.update_positions_observation_state('600000', True)
```

### 3. BacktestDataAdapter（回测系统适配器）

特点：
- 从数据库查询数据并转换为 backtrader 格式
- 返回包含 `datetime` 索引的 DataFrame
- 提供数据验证功能
- 不需要持仓信息

使用示例：
```python
from shared.data import BacktestDataAdapter

data_adapter = BacktestDataAdapter()

# 获取股票数据
df = data_adapter.get_stock_data('600000', '2024-01-01', '2024-12-31', min_days=60)

# 验证数据
if data_adapter.validate_data_for_backtest(df):
    # 数据可以直接用于 backtrader
    pass
```

### 4. IndicatorsCalculator（指标计算器）

特点：
- 统一的指标计算逻辑
- 支持信号系统和回测系统
- 返回标准化的指标字典

使用示例：
```python
from shared.data import IndicatorsCalculator

calc = IndicatorsCalculator()
indicators = calc.calculate(df, '600000')
```

## 数据格式

### 信号系统数据格式

```python
{
    'code': '600000',
    'close': 10.5,
    'open': 10.3,
    'high': 10.6,
    'low': 10.2,
    'volume': 1000000,
    'close_arr': array([...]),
    'open_arr': array([...]),
    'high_arr': array([...]),
    'low_arr': array([...]),
    'volume_arr': array([...]),
    '涨幅': 2.5,
    '振幅': 3.8,
    'dif': 0.05,
    'k': 50.0,
    'd': 45.0,
    'j': 60.0,
    '知行短期趋势线': 10.4,
    '知行多空线': 10.2,
    # ... 更多指标
}
```

### 回测系统数据格式

```python
# DataFrame with datetime index
                    open    high     low   close    volume  openinterest
datetime
2024-01-01  10.3  10.6  10.2  10.5  1000000  5000000
2024-01-02  10.5  10.8  10.4  10.7  1200000  6000000
...
```

## 迁移指南

### 信号系统迁移

**旧代码：**
```python
from signals.singal_cal.basic_module import calculate_indicators

def get_stock_data(code, trading_date, days=150):
    conn = duckdb.connect(DB_PATH, read_only=True)
    ts_code = code_to_ts_code(code)
    df = conn.execute("""
        SELECT ts_code, trade_date, open, high, low, close, vol
        FROM dwd_daily_price
        WHERE ts_code = ? AND trade_date <= ?
        ORDER BY trade_date DESC LIMIT ?
    """, [ts_code, trading_date, days]).fetchdf()
    conn.close()
    return df

df = get_stock_data('600000', '2026-04-17', 150)
indicators = calculate_indicators(df)
```

**新代码：**
```python
from shared.data import SignalDataAdapter

data_adapter = SignalDataAdapter()
df = data_adapter.get_stock_data_by_trading_date('600000', '2026-04-17', days=150)
indicators = data_adapter.calculate_indicators(df, '600000')
```

### 回测系统迁移

**旧代码：**
```python
def get_data_from_astock3(stock_code, start_date, end_date):
    db = duckdb.connect(str(ASTOCK3_DB_PATH))
    df = db.execute(f"""
        SELECT trade_date, ts_code, open, high, low, close, vol, amount
        FROM dwd_daily_price 
        WHERE ts_code = '{stock_code}' 
        AND trade_date >= '{start_date_fmt}' 
        AND trade_date <= '{end_date_fmt}'
        ORDER BY trade_date
    """).fetchdf()
    db.close()
    df = df.rename(columns={'trade_date': 'date', 'ts_code': 'code', 'vol': 'volume'})
    return df
```

**新代码：**
```python
from shared.data import BacktestDataAdapter

data_adapter = BacktestDataAdapter()
df = data_adapter.get_stock_data('600000', '2024-01-01', '2024-12-31', min_days=60)
```

## 优势

1. **统一接口**：信号系统和回测系统使用相同的数据获取方式
2. **代码复用**：指标计算逻辑只实现一次
3. **易于维护**：数据源变更只需修改适配器
4. **类型安全**：统一的返回格式
5. **易于测试**：可以轻松 mock 数据适配器

## 使用示例

查看 `usage_examples.py` 获取完整的使用示例：

```bash
python shared/data/usage_examples.py
```

## 注意事项

1. 股票代码统一使用 6 位数字格式（如 '600000'）
2. 日期格式统一使用 'YYYY-MM-DD' 格式
3. 信号系统需要持仓信息，回测系统不需要
4. 回测系统返回的数据包含 datetime 索引，可直接用于 backtrader
