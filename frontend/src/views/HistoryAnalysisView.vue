<script setup lang="ts">
/**
 * 历史交易综合分析页面
 * 
 * 数据来源表:
 * - portfolio_daily: 净值曲线数据 (date, init_cash, total_value)
 * - v_position_analysis: 历史交易视图 (positions + dwd_stock_info + dwd_daily_basic)
 *   - positions: 交易记录主表 (code, name, buy_date, sell_date, profit_loss, buy_price, shares, stop_loss_pct)
 *   - dwd_stock_info: 股票基础信息 (symbol, industry)
 *   - dwd_daily_basic: 每日指标 (ts_code, trade_date, total_mv)
 * 
 * 计算说明:
 * - 期望值(R) = (胜率 × 平均盈利R) - (败率 × 1)
 * - 每笔风险金额 = buy_price × shares × stop_loss_pct (止损比例3%)
 */

import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { Line, Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler } from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler)

interface Summary {
  total_trades: number
  total_profit: number
  win_rate: number
  avg_holding_days: number
  annualized_return: number
  cumulative_return: number
  volatility: number
  sharpe_ratio: number
  sortino_ratio: number
  max_drawdown: number
  max_drawdown_duration: number
  calmar_ratio: number
  profit_loss_ratio: number
  expectancy: number
  expectancy_r: number
  best_trade: number
  worst_trade: number
  avg_profit: number
  avg_loss: number
  avg_drawdown: number
}

interface SignalAnalysis {
  signal_name: string
  signal_type: string
  trade_count: number
  win_count: number
  win_rate: number
  total_profit: number
  avg_profit_per_trade: number
  avg_holding_days: number
}

interface IndustryAnalysis {
  industry: string
  trade_count: number
  win_count: number
  win_rate: number
  total_profit: number
  avg_holding_days: number
}

interface MarketCapAnalysis {
  group: string
  group_code: string
  trade_count: number
  win_count: number
  win_rate: number
  total_profit: number
}

interface HoldingDistribution {
  '0-5天': number
  '6-10天': number
  '11-20天': number
  '21-30天': number
  '30天以上': number
}

interface MonthlyReturn {
  month: string
  trade_count: number
  profit: number
  win_rate: number
}

const loading = ref(true)
const marketCapAnalysis = ref<MarketCapAnalysis[]>([])

const analysisData = ref<{
  summary: Summary
  by_signal_type: SignalAnalysis[]
  by_industry: IndustryAnalysis[]
  by_market_cap: MarketCapAnalysis[]
  holding_period_distribution: HoldingDistribution
  monthly_returns: MonthlyReturn[]
} | null>(null)

const fetchAnalysis = async () => {
  try {
    loading.value = true
    const res = await axios.get('/api/history/analysis')
    analysisData.value = res.data
    marketCapAnalysis.value = analysisData.value?.by_market_cap || []
  } catch (e) {
    console.error('Failed to fetch analysis:', e)
  } finally {
    loading.value = false
  }
}

const formatMoney = (value: number | undefined | null) => {
  if (value === null || value === undefined) return '--'
  const absValue = Math.abs(value)
  if (absValue >= 10000) {
    return (value >= 0 ? '+' : '') + (value / 10000).toFixed(2) + '万'
  }
  return (value >= 0 ? '+' : '') + value.toFixed(2)
}

const formatNumber = (value: number | undefined | null, decimals: number = 2): string => {
  if (value === null || value === undefined) return '--'
  return value.toFixed(decimals)
}

// 持仓时间分布柱状图数据
const holdingChartData = computed(() => {
  if (!analysisData.value) return null
  const dist = analysisData.value.holding_period_distribution
  return {
    labels: Object.keys(dist),
    datasets: [{
      label: '交易次数',
      data: Object.values(dist),
      backgroundColor: 'rgba(59, 130, 246, 0.6)',
      borderColor: 'rgba(59, 130, 246, 1)',
      borderWidth: 1
    }]
  }
})

const holdingChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b' }
    },
    y: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b', stepSize: 1 }
    }
  }
}

// 月度收益折线图数据
const monthlyChartData = computed(() => {
  if (!analysisData.value) return null
  const returns = analysisData.value.monthly_returns
  return {
    labels: returns.map(r => r.month),
    datasets: [{
      label: '月度收益率',
      data: returns.map(r => r.profit),
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderWidth: 2,
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: '#3b82f6'
    }]
  }
})

const monthlyChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      callbacks: {
        label: (context: any) => `收益: ${formatMoney(context.parsed.y)}`
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b' }
    },
    y: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b' }
    }
  }
}

onMounted(() => {
  fetchAnalysis()
})
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <div class="flex items-center gap-4 mb-6">
      <router-link to="/" class="text-slate-400 hover:text-slate-200">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </router-link>
      <h1 class="text-2xl font-bold text-slate-100">历史交易综合分析</h1>
    </div>
    
    <!-- 数据来源信息 -->
    <div class="glass-card p-4 mb-6">
      <div class="flex items-center gap-2 mb-2">
        <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span class="text-sm text-slate-300 font-medium">数据来源</span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
        <div>
          <span class="text-slate-500">净值曲线:</span>
          <span class="text-slate-300 ml-1">portfolio_daily</span>
        </div>
        <div>
          <span class="text-slate-500">交易记录:</span>
          <span class="text-slate-300 ml-1">positions</span>
        </div>
        <div>
          <span class="text-slate-500">行业信息:</span>
          <span class="text-slate-300 ml-1">dwd_stock_info</span>
        </div>
        <div>
          <span class="text-slate-500">市值分组:</span>
          <span class="text-slate-300 ml-1">dwd_daily_basic</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12 text-slate-400">
      加载中...
    </div>

    <!-- No Data State -->
    <div v-else-if="!analysisData?.summary" class="text-center py-12 text-slate-400">
      暂无历史交易数据
    </div>

    <div v-else class="space-y-6">
      <!-- 概览卡片 - 分组布局 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <!-- 收益维度 -->
        <div class="glass-card p-5">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              </svg>
            </div>
            <p class="text-slate-400 text-sm">总盈亏</p>
          </div>
          <p class="text-3xl font-bold tracking-tight" :class="(analysisData.summary.total_profit ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
            {{ formatMoney(analysisData.summary.total_profit) }}
          </p>
          <p class="text-slate-500 text-xs mt-1">{{ analysisData.summary.total_trades }} 笔交易</p>
        </div>

        <div class="glass-card p-5">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-600/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </div>
            <p class="text-slate-400 text-sm">累计收益率</p>
          </div>
          <p class="text-3xl font-bold tracking-tight" :class="(analysisData.summary.cumulative_return ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
            {{ formatNumber(analysisData.summary.cumulative_return, 2) }}%
          </p>
          <p class="text-slate-500 text-xs mt-1">年化 {{ formatNumber(analysisData.summary.annualized_return, 1) }}%</p>
        </div>

        <div class="glass-card p-5">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-purple-600/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
              </svg>
            </div>
            <p class="text-slate-400 text-sm">夏普比率</p>
          </div>
          <p class="text-3xl font-bold tracking-tight" :class="(analysisData.summary.sharpe_ratio ?? 0) < 1 ? 'text-green-400' : 'text-red-400'">
            {{ formatNumber(analysisData.summary.sharpe_ratio, 2) }}
          </p>
          <p class="text-slate-500 text-xs mt-1">索提诺 {{ formatNumber(analysisData.summary.sortino_ratio, 2) }}</p>
        </div>

        <div class="glass-card p-5">
          <div class="flex items-center gap-3 mb-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500/20 to-red-600/20 flex items-center justify-center">
              <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"></path>
              </svg>
            </div>
            <p class="text-slate-400 text-sm">最大回撤</p>
          </div>
          <p class="text-3xl font-bold tracking-tight" :class="(analysisData.summary.max_drawdown ?? 0) < 0 ? 'text-green-400' : 'text-red-400'">
            {{ formatNumber(analysisData.summary.max_drawdown, 1) }}%
          </p>
          <p class="text-slate-500 text-xs mt-1">持续 {{ analysisData.summary.max_drawdown_duration }} 天</p>
        </div>
      </div>

      <!-- 交易质量模块 - 横向大卡片 -->
      <div class="glass-card p-6">
        <h2 class="text-lg font-semibold text-slate-100 mb-4">交易质量总览</h2>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
          <!-- 胜率 -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">胜率</p>
            <p class="text-3xl font-bold text-slate-100 mb-1">{{ formatNumber(analysisData.summary.win_rate, 1) }}%</p>
            <div class="w-full bg-slate-700 rounded-full h-1.5">
              <div class="bg-blue-500 h-1.5 rounded-full transition-all" :style="{ width: analysisData.summary.win_rate + '%' }"></div>
            </div>
          </div>
          
          <!-- 盈亏比 -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">盈亏比</p>
            <p class="text-3xl font-bold" :class="(analysisData.summary.profit_loss_ratio ?? 0) < 1 ? 'text-green-400' : 'text-red-400'">
              {{ formatNumber(analysisData.summary.profit_loss_ratio, 2) }}
            </p>
            <p class="text-slate-500 text-xs mt-1">均值 2.46</p>
          </div>
          
          <!-- 期望值 -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">期望值</p>
            <p class="text-3xl font-bold" :class="(analysisData.summary.expectancy ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
              {{ formatMoney(analysisData.summary.expectancy) }}
            </p>
            <p class="text-slate-500 text-xs mt-1">每笔平均</p>
          </div>
          
          <!-- 期望值(R) -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">期望值(R)</p>
            <p class="text-3xl font-bold" :class="(analysisData.summary.expectancy_r ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
              {{ (analysisData.summary.expectancy_r ?? 0).toFixed(3) }}R
            </p>
            <p class="text-slate-500 text-xs mt-1">止损3%/笔</p>
          </div>
          
          <!-- 最大单次盈利 -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">最大单笔盈利</p>
            <p class="text-3xl font-bold text-red-400">{{ formatMoney(analysisData.summary.best_trade) }}</p>
            <p class="text-slate-500 text-xs mt-1">最佳交易</p>
          </div>
          
          <!-- 最大单次亏损 -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">最大单笔亏损</p>
            <p class="text-3xl font-bold text-green-400">{{ formatMoney(analysisData.summary.worst_trade) }}</p>
            <p class="text-slate-500 text-xs mt-1">最差交易</p>
          </div>
          
          <!-- 平均持仓 -->
          <div class="text-center">
            <p class="text-slate-400 text-sm mb-2">平均持仓</p>
            <p class="text-3xl font-bold text-slate-100">{{ formatNumber(analysisData.summary.avg_holding_days, 1) }}天</p>
            <p class="text-slate-500 text-xs mt-1">短线策略</p>
          </div>
        </div>
      </div>
      
      <!-- 风险指标详情 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="glass-card p-4 text-center">
          <p class="text-slate-400 text-xs mb-2">年化波动率</p>
          <p class="text-2xl font-bold text-slate-100">{{ formatNumber(analysisData.summary.volatility, 1) }}%</p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-slate-400 text-xs mb-2">索提诺比率</p>
          <p class="text-2xl font-bold" :class="(analysisData.summary.sortino_ratio ?? 0) < 1 ? 'text-green-400' : 'text-red-400'">
            {{ formatNumber(analysisData.summary.sortino_ratio, 2) }}
          </p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-slate-400 text-xs mb-2">卡玛比率</p>
          <p class="text-2xl font-bold" :class="(analysisData.summary.calmar_ratio ?? 0) < 1 ? 'text-green-400' : 'text-red-400'">
            {{ formatNumber(analysisData.summary.calmar_ratio, 2) }}
          </p>
        </div>
        <div class="glass-card p-4 text-center">
          <p class="text-slate-400 text-xs mb-2">平均回撤</p>
          <p class="text-2xl font-bold" :class="(analysisData.summary.avg_drawdown ?? 0) < 0 ? 'text-green-400' : 'text-red-400'">
            {{ formatNumber(analysisData.summary.avg_drawdown, 2) }}%
          </p>
        </div>
      </div>

      <!-- 按信号类型分析 -->
      <div class="glass-card p-4">
        <h2 class="text-lg font-semibold text-slate-100 mb-4">按信号类型分析</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="text-left py-3 px-2 text-slate-400 font-medium">信号名称</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">交易次数</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">盈利次数</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">胜率</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">总盈亏</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">平均每笔</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">平均持仓</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="signal in analysisData.by_signal_type" 
                :key="signal.signal_name"
                class="border-b border-slate-800 hover:bg-slate-800/30"
              >
                <td class="py-3 px-2 text-slate-100">{{ signal.signal_name }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ signal.trade_count }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ signal.win_count }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ formatNumber(signal.win_rate, 1) }}%</td>
                <td class="py-3 px-2 text-right font-medium" :class="(signal.total_profit ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
                  {{ formatMoney(signal.total_profit) }}
                </td>
                <td class="py-3 px-2 text-right" :class="(signal.avg_profit_per_trade ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
                  {{ formatMoney(signal.avg_profit_per_trade) }}
                </td>
                <td class="py-3 px-2 text-right text-slate-300">{{ formatNumber(signal.avg_holding_days, 1) }}天</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 持仓时间分布 & 月度收益 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- 持仓时间分布 -->
        <div class="glass-card p-4">
          <h2 class="text-lg font-semibold text-slate-100 mb-4">持仓时间分布</h2>
          <div v-if="holdingChartData" class="h-64">
            <Bar :data="holdingChartData" :options="holdingChartOptions" />
          </div>
        </div>

        <!-- 月度收益趋势 -->
        <div class="glass-card p-4">
          <h2 class="text-lg font-semibold text-slate-100 mb-4">月度收益趋势</h2>
          <div v-if="monthlyChartData" class="h-64">
            <Line :data="monthlyChartData" :options="monthlyChartOptions" />
          </div>
        </div>
      </div>

      <!-- 按行业分析 -->
      <div class="glass-card p-4">
        <h2 class="text-lg font-semibold text-slate-100 mb-4">按行业分析</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="text-left py-3 px-2 text-slate-400 font-medium">行业</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">交易次数</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">盈利次数</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">胜率</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">总盈亏</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="industry in analysisData.by_industry" 
                :key="industry.industry"
                class="border-b border-slate-800 hover:bg-slate-800/30"
              >
                <td class="py-3 px-2 text-slate-100">{{ industry.industry || '未知' }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ industry.trade_count }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ industry.win_count }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ formatNumber(industry.win_rate, 1) }}%</td>
                <td class="py-3 px-2 text-right font-medium" :class="(industry.total_profit ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
                  {{ formatMoney(industry.total_profit) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 按市值分组分析 -->
      <div class="glass-card p-4">
        <h2 class="text-lg font-semibold text-slate-100 mb-4">按市值分组分析</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="text-left py-3 px-2 text-slate-400 font-medium">市值分组</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">交易次数</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">胜率</th>
                <th class="text-right py-3 px-2 text-slate-400 font-medium">总盈亏</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                v-for="item in marketCapAnalysis" 
                :key="item.group"
                class="border-b border-slate-800 hover:bg-slate-800/30"
              >
                <td class="py-3 px-2 text-slate-100">{{ item.group }}</td>
                <td class="py-3 px-2 text-right text-slate-300">{{ item.trade_count }}</td>
                <td class="py-3 px-2 text-right" :class="(item.win_rate ?? 0) < 50 ? 'text-green-400' : 'text-red-400'">
                  {{ formatNumber(item.win_rate, 1) }}%
                </td>
                <td class="py-3 px-2 text-right" :class="(item.total_profit ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'">
                  {{ formatMoney(item.total_profit) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
    </div>
    </div>
  </div>
</template>

<style scoped>
.glass-card {
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid #334155;
  border-radius: 12px;
}
</style>