# A股量化交易回测系统 - 安装指南

本文档详细说明如何在全新环境中安装和配置本系统。

## 目录

- [环境要求](#环境要求)
- [第一步：克隆项目](#第一步克隆项目)
- [第二步：安装 Python 环境](#第二步安装-python-环境)
- [第三步：安装前端环境](#第三步安装前端环境)
- [第四步：安装 Python 依赖](#第四步安装-python-依赖)
- [第五步：安装前端依赖](#第五步安装前端依赖)
- [第六步：配置环境变量](#第六步配置环境变量)
- [第七步：配置 AI Agent（如需使用）](#第七步配置-ai-agent如需使用)
- [第八步：初始化数据库](#第八步初始化数据库)
- [第九步：启动dashboard](#第九步启动dashboard)

---

## 环境要求

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|----------|----------|------|
| Python | 3.8 | 3.10 | 数据处理需要 |
| Node.js | 18 | 20 LTS | 前端构建需要 |
| npm | 8.0 | 10.0 | 包管理 |
| 操作系统 | Windows 10 / macOS 10.14 / Ubuntu 18.04 | Windows 11 / macOS 13 / Ubuntu 22.04 | 支持三大平台 |
| 内存 | 4GB | 8GB+ | 数据处理需要较大内存 |
| 硬盘 | 10GB | 20GB+ | 数据存储需要 |

---

## 第一步：克隆项目

```bash
git clone <项目仓库地址>
cd Silverquant
```

如果未使用 git，可以直接下载 ZIP 包并解压。

---

## 第二步：安装 Python 环境

### 方式一：使用 conda（推荐）

```bash
# 创建 Python 3.10 环境
conda create -n silverquant python=3.10

# 激活环境
conda activate silverquant
```

### 方式二：使用 venv

```bash
# 进入项目目录
cd Silverquant

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 方式三：使用 pyenv（Linux/Mac）

```bash
pyenv install 3.10.12
pyenv local 3.10.12
```

> **注意**：建议使用 conda 或 venv 创建独立环境，避免与系统其他 Python 项目冲突。

---

## 第三步：安装前端环境

### 安装 Node.js

#### macOS

```bash
# 使用 Homebrew 安装
brew install node

# 或使用 nvm（推荐）
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.zshrc
nvm install 18
nvm use 18
```

#### Windows

下载并安装 [Node.js 安装包](https://nodejs.org/)，选择 LTS 版本。

#### Linux (Ubuntu/Debian)

```bash
# 使用 nvm 安装
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
```

### 验证安装

```bash
node -v   # 应显示 v18.x.x 或更高
npm -v    # 应显示 8.x.x 或更高
```

---

## 第四步：安装 Python 依赖

### 基础安装

```bash
# 确保已激活 Python 环境
# (conda activate silverquant) 或 (source venv/bin/activate)

# 安装依赖
pip install -r requirements.txt
```

### 逐个安装（可选，如遇问题）

```bash
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install duckdb>=0.9.0
pip install akshare>=1.12.0
pip install baostock>=0.8.8
pip install tushare>=1.4.0
pip install backtrader>=1.9.78
pip install flask>=3.0.0
pip install flask-cors>=4.0.0
pip install langchain-core>=0.1.0
pip install pydantic>=2.0.0
pip install matplotlib>=3.7.0
pip install seaborn>=0.12.0
pip install scipy>=1.11.0
pip install requests>=2.31.0
pip install tqdm>=4.66.0
pip install python-dateutil>=2.8.0
pip install sqlalchemy>=2.0.0
pip install pytest>=7.4.0
```

### 验证 Python 依赖

```bash
python -c "
import pandas as pd
import numpy as np
import duckdb
import akshare as ak
import baostock as bs
import backtrader as bt
import flask
print('所有 Python 依赖安装成功！')
"
```

---

## 第五步：安装前端依赖

```bash
cd frontend

# 使用 npm 安装依赖
npm install

# 如果安装速度慢，可使用淘宝镜像
npm install --registry=https://registry.npmmirror.com
```

### 验证前端依赖

```bash
npm run dev
```

如果看到类似 `VITE v5.x.x ready in xxx ms`，表示安装成功。按 `Ctrl+C` 停止开发服务器。

---

## 第六步：配置环境变量

### 创建 .env 文件

项目使用 `.env` 文件管理所有敏感配置。在项目根目录创建 `.env` 文件：

```bash
# 在项目根目录创建 .env 文件
touch .env
```

### 编辑 .env 文件

```bash
# 使用文本编辑器打开
# Linux/Mac:
nano .env
# 或
vim .env

# Windows:
notepad .env
```

### .env 文件内容

```env
# ========================
# 数据源配置
# ========================

# tushare token（重要：用于获取 A 股数据）
# 获取地址：https://tushare.pro/register
TUSHARE_TOKEN='your_tushare_token_here'

# ========================
# AI Agent LLM 配置
# ========================

# DeepSeek API Key（用于 AI Agent 分析）
# 获取地址：https://platform.deepseek.com/
DEEPSEEK_API_KEY='your_deepseek_api_key_here'

# MiniMax API Key（可选，用于 AI Agent 分析）
# 获取地址：https://www.minimaxi.com/
MINIMAX_API_KEY='your_minimax_api_key_here'

# MiniMax Group ID（使用 MiniMax 时需要）
MINIMAX_GROUP_ID='your_minimax_group_id_here'
```

### 配置说明

| 变量名 | 必需 | 说明 |
|--------|------|------|
| `TUSHARE_TOKEN` | 建议配置 | tushare 数据源 token，用于获取 A 股数据 |
| `DEEPSEEK_API_KEY` | 可选  | DeepSeek API Key |
| `MINIMAX_API_KEY` | 可选 | MiniMax API Key |

### 验证 .env 配置

```bash
# 测试环境变量是否正确加载
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('TUSHARE_TOKEN:', '已设置' if os.getenv('TUSHARE_TOKEN') else '未设置')
print('DEEPSEEK_API_KEY:', '已设置' if os.getenv('DEEPSEEK_API_KEY') else '未设置')
print('MINIMAX_API_KEY:', '已设置' if os.getenv('MINIMAX_API_KEY') else '未设置')
"
```

### 数据源优先级

系统支持多数据源自动切换，优先级可在 `config/settings.py` 中配置：

```python
DATA_SOURCE_PRIORITY = ['tushare', 'baostock']  # 默认优先级
```

---

## 第七步：配置 AI Agent（如需使用）

### 概述

`agent_integration` 模块提供 AI 驱动的股票分析功能，包括：

- 多 Agent 协作分析（市场分析、基本面分析、新闻分析）
- 股票研究（多头/空头研究）
- 风险管理（保守/中性/激进辩论）
- 交易决策图谱

### 支持的大模型

| 提供商 | 模型 | 说明 |
|--------|------|------|
| DeepSeek | deepseek-chat | 对话模型 |
| DeepSeek | deepseek-coder | 代码模型 |
| DeepSeek | deepseek-reasoner | 推理模型 |
| MiniMax | MiniMax-M2.7 | MiniMax M2.7 模型 |
| MiniMax | MiniMax-M2 | MiniMax M2 模型 |

### API Key 配置

在 `.env` 文件中配置至少一个 LLM 提供商的 API Key：

```env
# DeepSeek 配置（推荐）
DEEPSEEK_API_KEY='your_deepseek_api_key'

# 或 MiniMax 配置
MINIMAX_API_KEY='your_minimax_api_key'
```

### 使用示例

#### 基本使用

```python
from agent_integration.api.analyzer import analyze_stock
from agent_integration.llm_adapters.factory import create_llm_by_provider

# 分析单只股票
result = analyze_stock(
    stock_code='600000',
    provider='deepseek',  # 或 'minimax'
    model='deepseek-chat'
)
print(result)
```

#### 批量分析

```python
from agent_integration.api.batch_analyzer import batch_analyze

# 批量分析多只股票
results = batch_analyze(
    stock_codes=['600000', '000001', '300001'],
    provider='deepseek',
    model='deepseek-chat',
    max_workers=3
)
```

#### 交易图谱

```python
from agent_integration.graph.trading_graph import TradingAgentsGraph

# 创建交易图谱
graph = TradingAgentsGraph(provider='deepseek', model='deepseek-chat')
result = graph.analyze('600000')
```

### Agent 模块结构

```
agent_integration/
├── api/                    # API 接口
│   ├── analyzer.py        # 单股分析
│   └── batch_analyzer.py  # 批量分析
├── agents/                # Agent 实现
│   ├── analysts/          # 分析师
│   │   ├── market_analyst.py       # 市场分析师
│   │   ├── fundamentals_analyst.py # 基本面分析师
│   │   └── news_analyst.py         # 新闻分析师
│   ├── researchers/       # 研究员
│   │   ├── bull_researcher.py     # 多头研究员
│   │   └── bear_researcher.py     # 空头研究员
│   └── risk_mgmt/        # 风险管理
│       ├── conservative_debator.py  # 保守派
│       ├── neutral_debator.py       # 中立派
│       └── aggressive_debator.py   # 激进派
├── llm_adapters/         # LLM 适配器
│   ├── base.py           # 基类
│   ├── deepseek.py      # DeepSeek 适配器
│   ├── minimax.py       # MiniMax 适配器
│   └── factory.py       # 工厂函数
├── dataflows/           # 数据流
│   ├── news/            # 新闻数据
│   ├── markets/         # 市场数据
│   └── adapters/        # 数据适配器
├── memory/              # 记忆管理
├── cache/               # 缓存
├── graph/               # 交易图谱
└── examples/            # 使用示例
```

---

## 第八步：初始化数据库

## 快速开始

### 一行命令完成所有初始化

```bash
cd /Users/mawenhao/Desktop/code/股票策略

# 1. 创建数据库并初始化所有表
python scripts/init_database.py

# 2. 下载日线数据（建议至少6个月）
# 使用 DWDFetcher，支持 tushare 和 baostock 两个数据源
# 默认使用 tushare，可通过 DATA_SOURCE 环境变量切换
python data/updaters/fetcher_dwd.py --start 20250101 --end 20260430

# 或使用 baostock（按股票下载，适合首次全量下载）
DATA_SOURCE=baostock python data/updaters/fetcher_dwd.py --start 20250101 --end 20260430

# 3. 下载指数数据（可选）
python data/updaters/fetcher_index_daily.py --all
```

完成以上步骤后，系统即可正常运行信号扫描和回测功能。

---

## 系统要求

- Python 3.8+
- DuckDB
- 磁盘空间：至少 10GB（用于存储历史数据）

### 必需依赖

```bash
pip install duckdb pandas numpy akshare baostock tushare backtrader
```

---

## 详细内容可以看“数据初始化.md”
---

## 第九步：启动 Dashboard

Dashboard 是基于 Flask + Vue 的 Web 可视化界面，用于监控交易状态、查看回测结果和分析信号策略。

---

### 启动 Dashboard

#### 方式一：直接启动（推荐）

```bash
# 确保已激活 Python 环境
conda activate silverquant  # 或 source venv/bin/activate

# 进入项目根目录
cd /Users/mawenhao/Desktop/code/silverquant/Silverquant

# 启动 Dashboard
python dashboard/app.py
```

#### 方式二：使用后台运行

```bash
# Linux/Mac - 使用 nohup 后台运行
nohup python dashboard/app.py > dashboard.log 2>&1 &

# 查看日志
tail -f dashboard.log

# 查看进程
ps aux | grep dashboard/app.py
```

#### 方式三：使用 PM2 管理（生产环境推荐）

```bash
# 安装 PM2
npm install -g pm2

# 启动并命名为 silverquant-dashboard
pm2 start dashboard/app.py --name silverquant-dashboard

# 查看状态
pm2 status

# 查看日志
pm2 logs silverquant-dashboard

# 重启
pm2 restart silverquant-dashboard

# 停止
pm2 stop silverquant-dashboard
```

---

### 访问 Dashboard

启动成功后，在浏览器中打开：

```
http://localhost:5004
```

如果是远程服务器，将 `localhost` 替换为服务器 IP 地址：

```
http://<服务器IP>:5004
```

---

### Dashboard 功能概览

| 页面 | 路径 | 说明 |
|------|------|------|
| 首页 | `/` | 组合概览、权益曲线、策略对比 |
| 信号 | `/signals` | 买入/卖出信号列表 |
| 持仓 | `/positions` | 当前持仓管理 |
| 历史 | `/history` | 历史交易记录 |
| 多信号共振 | `/multi-signal-resonance` | 多策略共振股票分析 |
| 数据更新 | `/data-update` | 数据更新管理 |
| Agent | `/agent` | AI Agent 分析功能 |
| Agent 历史 | `/agent/history` | AI 分析历史记录 |

---

### 关闭 Dashboard

#### 方法一：直接停止（如果在前台运行）

在运行 Dashboard 的终端按 `Ctrl+C`

#### 方法二：停止后台进程

```bash
# 查找进程
ps aux | grep dashboard/app.py

# 杀死进程（假设 PID 是 12345）
kill 12345

# 或使用 pkill
pkill -f "dashboard/app.py"
```

#### 方法三：使用 PM2 停止

```bash
pm2 stop silverquant-dashboard
pm2 delete silverquant-dashboard
```

---

### 验证 Dashboard 是否正常运行

```bash
# 检查端口是否被占用
lsof -i :5004

# 测试 API 是否响应
curl http://localhost:5004/api/stats

# 应该返回类似：
# {"holding_count": 5, "sold_count": 20, "today_buy_signals": 12, "latest_date": "2026-04-29"}
```

---

### 常见问题

#### Q1: 端口 5004 已被占用

```bash
# 方法1：更换端口
# 编辑 dashboard/app.py，将 port=5004 改为其他端口如 5005

# 方法2：查找并停止占用进程
lsof -i :5004
kill <PID>
```

#### Q2: 前端页面空白

```bash
# 检查前端是否已构建
ls -la frontend/dist/

# 如果没有，构建前端
cd frontend
npm run build
```

#### Q3: 数据库连接失败

```bash
# 检查数据库文件是否存在
ls -la data/Astock3.duckdb

# 如果不存在，先初始化数据库
python scripts/init_database.py
```

#### Q4: 想开机自启动

```bash
# Mac - 使用 launchd
# 创建 ~/Library/LaunchAgents/com.silverquant.dashboard.plist

# Linux - 使用 systemd
# 创建 /etc/systemd/system/silverquant-dashboard.service
```

---

### 快速命令汇总

```bash
# 启动
conda activate silverquant
python dashboard/app.py

# 后台运行
nohup python dashboard/app.py > dashboard.log 2>&1 &

# 检查状态
curl http://localhost:5004/api/stats

# 停止
pkill -f "dashboard/app.py"
```
