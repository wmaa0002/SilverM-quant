# 回测模块升级 - 完整使用指南

## 概述

本文档详细介绍如何将策略注册到系统中、执行回测、并通过可视化界面查看结果。

---

## 一、策略注册

### 1.1 策略文件结构

策略文件位于 `strategies/` 目录，必须继承 `BaseStrategy`：

```python
# strategies/我的策略.py
from strategies.base.framework_strategy import BaseStrategy

class 我的策略(BaseStrategy):
    """我的自定义策略"""
    
    params = (
        ('threshold', 8.0),      # 评分阈值
        ('stop_loss_pct', 0.05), # 止损比例
    )
    
    def calculate_score(self):
        """计算策略评分 - 必须实现"""
        # ... 策略逻辑
        return score
    
    def buy_condition(self):
        """买入条件 - 必须实现"""
        return self.score > self.params.threshold
    
    def sell_condition(self):
        """卖出条件 - 可选"""
        return False
```

### 1.2 注册策略（两种方式）

#### 方式一：使用装饰器（推荐）

在策略文件末尾添加 `@register` 装饰器：

```python
# strategies/我的策略.py
from strategies.base.framework_strategy import BaseStrategy
from strategies.registry import register

class 我的策略(BaseStrategy):
    params = (
        ('threshold', 8.0),
    )
    
    def calculate_score(self):
        return self.score > self.params.threshold
    
    def buy_condition(self):
        return self.calculate_score() > self.params.threshold

# 注册策略
@register(
    name='我的策略',
    threshold_required=True,     # 是否需要 threshold 参数
    min_data_days=60,           # 最少需要的历史数据天数
    description='这是一个测试策略'  # 策略描述
)
class 我的策略:
    pass
```

#### 方式二：手动注册

```python
from strategies.registry import Registry, StrategyMetadata

registry = Registry()

metadata = StrategyMetadata(
    name='我的策略',
    threshold_required=True,
    min_data_days=60,
    description='手动注册的策略'
)

registry.register('我的策略', metadata)
```

### 1.3 验证注册成功

```bash
python -c "
from strategies.registry import Registry

registry = Registry()
print('已注册策略:', registry.list())
print('我的策略已注册:', registry.is_registered('我的策略'))
"
```

输出：
```
已注册策略: ['天宫B1策略v1', '天宫B2策略v2', '我的策略', ...]
我的策略已注册: True
```

---

## 二、执行回测

### 2.1 通过 Python API

```python
from backtest.engine import BacktestEngine
from strategies.registry import Registry

# 获取策略
registry = Registry()
StrategyClass = registry.get('天宫B2策略v2')

# 创建回测引擎
engine = BacktestEngine(
    # 策略参数
    strategy_class=StrategyClass,
    strategy_params={'threshold': 8.0},
    
    # 数据范围
    start_date='20240101',      # 开始日期 (YYYYMMDD)
    end_date='20240331',        # 结束日期
    
    # 股票筛选
    stock_list=['000001', '000002'],  # 指定股票
    # stock_file='stocks.txt'         # 或从文件加载
    
    # 资金参数
    initial_capital=1_000_000,  # 初始资金
)

# 运行回测
result = engine.run()

# 查看结果
print(f"总收益率: {result['total_return']:.2%}")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
print(f"最大回撤: {result['max_drawdown']:.2%}")
```

### 2.2 通过 CLI

```bash
# 使用注册表运行
python backtest/strategy_backtest/batch_backtest_V3.py -l 1 --strategy 天宫B2策略v2

# 使用配置文件
python backtest/strategy_backtest/batch_backtest_V3.py -l 1 --config config.yaml
```

### 2.3 通过 REST API

```bash
# 启动后端服务
python dashboard/app.py

# 运行回测
curl -X POST http://localhost:5004/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "天宫B2策略v2",
    "start_date": "20240101",
    "end_date": "20240331",
    "stock_list": ["000001", "000002"],
    "initial_capital": 1000000
  }'
```

响应：
```json
{
  "run_id": "20260411_143052",
  "status": "completed",
  "metrics": {
    "total_return": 0.1523,
    "annual_return": 0.6120,
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.0823,
    "win_rate": 0.65
  }
}
```

---

## 三、数据可视化

### 3.1 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000`

### 3.2 页面功能

#### 3.2.1 回测 Dashboard（首页）

1. **选择策略**：从下拉菜单选择已注册策略
2. **设置日期**：选择回测时间段
3. **选择股票**：全部 / 单只 / 列表
4. **设置资金**：输入初始资金
5. **运行回测**：点击按钮

回测完成后显示：
- 关键指标卡片（收益率、夏普比率、最大回撤等）
- 收益曲线图
- 指标对比柱状图

#### 3.2.2 回测历史

路径：`/history`

功能：
- 表格展示所有历史回测
- 支持分页、排序、筛选
- 点击行查看详情

#### 3.2.3 回测详情

路径：`/detail/<run_id>`

功能：
- **收益曲线**：展示资金变化
- **交易记录**：买入/卖出详细
- **每日盈亏**：每日收益柱状图
- **回撤图**：资金回落可视化

#### 3.2.4 策略对比

路径：`/compare`

功能：
- 选择 2-5 个策略
- 对比收益曲线
- 对比关键指标（夏普、胜率、最大回撤）
- 月度收益热力图

### 3.3 导出数据

在详情页点击「导出」按钮：
- **CSV**：交易记录
- **JSON**：完整数据

---

## 四、完整示例

### 步骤 1：创建策略

```python
# strategies/我的双均线策略.py
from strategies.base.framework_strategy import BaseStrategy
from strategies.registry import register

class 双均线策略(BaseStrategy):
    params = (
        ('fast_ma', 5),    # 快速均线周期
        ('slow_ma', 20),   # 慢速均线周期
    )
    
    def calculate_score(self):
        fast = self.calculate_ma(self.params.fast_ma)
        slow = self.calculate_ma(self.params.slow_ma)
        return fast - slow  # 金叉死叉评分
    
    def buy_condition(self):
        ma5 = self.calculate_ma(5)
        ma20 = self.calculate_ma(20)
        return ma5 > ma20  # 金叉买入
    
    def sell_condition(self):
        ma5 = self.calculate_ma(5)
        ma20 = self.calculate_ma(20)
        return ma5 < ma20  # 死叉卖出

@register(
    name='双均线策略',
    threshold_required=False,
    min_data_days=60,
    description='简单双均线策略'
)
class 双均线策略:
    pass
```

### 步骤 2：验证注册

```bash
python -c "
from strategies.registry import Registry
r = Registry()
print('已注册:', '双均线策略' in r.list())
"
```

### 步骤 3：通过 API 运行回测

```bash
curl -X POST http://localhost:5004/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "双均线策略",
    "start_date": "20240101",
    "end_date": "20240601",
    "initial_capital": 1000000
  }'
```

### 步骤 4：查看结果

1. 打开 `http://localhost:3000`
2. 在历史页面找到刚运行的回测
3. 点击查看详情
4. 分析收益曲线和交易记录

---

## 五、架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                      Vue 3 前端                            │
│  (Dashboard / History / Detail / Compare)                 │
└─────────────────────┬─────────────────────────────────────┘
                      │ HTTP API
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Flask REST API                              │
│  (backtest_api.py)                                         │
│  - /api/backtest/run      运行回测                          │
│  - /api/backtest/history  历史记录                          │
│  - /api/backtest/strategies 策略列表                       │
└─────────────────────┬─────────────────────────────────────┘
                      │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐   ┌─────────────────────┐
│ Registry         │   │ BacktestEngine       │
│ (策略注册中心)    │   │ (回测引擎)           │
│ - @register     │   │ - date filter       │
│ - list()        │   │ - stock filter      │
│ - get()         │   │ - PerformanceMetrics│
└─────────────────┘   └─────────────────────┘
          │                     │
          ▼                     ▼
┌─────────────────┐   ┌─────────────────────┐
│ strategies/     │   │ DuckDB              │
│ (策略文件)       │   │ (市场数据)           │
└─────────────────┘   └─────────────────────┘
```

---

## 六、常见问题

### Q1: 策略未出现在下拉列表？

检查：
1. 策略文件是否在 `strategies/` 目录
2. 是否添加了 `@register` 装饰器
3. 装饰器参数 `name` 是否正确

### Q2: 回测报错"数据不足"？

策略需要 `min_data_days` 参数指定的最少历史数据：
```python
@register(name='我的策略', min_data_days=60)  # 需要60天数据
```

### Q3: 如何修改回测参数？

在 Dashboard 页面或 API 请求中修改：
- `initial_capital`: 初始资金
- `start_date` / `end_date`: 回测区间
- `stock_list`: 股票列表

---

## 七、文件清单

| 模块 | 文件 | 说明 |
|------|------|------|
| **注册中心** | `strategies/registry.py` | 策略注册表、@register 装饰器 |
| **回测引擎** | `backtest/engine.py` | 日期筛选、股票筛选、PerformanceMetrics |
| **REST API** | `dashboard/backtest_api.py` | 回测接口、历史接口 |
| **前端** | `frontend/src/views/` | Dashboard、History、Detail、Compare 页面 |
| **测试** | `tests/` | pytest 单元测试 (33 个测试用例) |
