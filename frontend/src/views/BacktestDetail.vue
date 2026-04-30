<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import axios from 'axios'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// Types
interface Trade {
  id: number
  run_id: string
  date: string
  datetime: string
  code: string
  name: string
  action: string
  price: number
  volume: number
  amount: number
  commission: number
  tax: number
  signal_type: string
}

interface DailyPnL {
  date: string
  total_value: number
  cash: number
  market_value: number
  daily_pnl: number
  daily_return: number
  cumulative_return: number
  benchmark_return: number
  excess_return: number
  drawdown: number
}

interface Metrics {
  total_return: number
  annualized_return: number
  benchmark_return: number
  excess_return: number
  volatility: number
  max_drawdown: number
  max_drawdown_duration: number
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  win_rate: number
  profit_loss_ratio: number
  total_trades: number
  // Batch-specific metrics (computed in backend)
  total_profit: number | null
  cumulative_return: number | null
  avg_drawdown: number | null
  expectancy: number | null
  // Unavailable metrics (marked as null in API response)
  expectancy_r: null
  best_trade: null
  worst_trade: null
  avg_profit: null
  avg_loss: null
  avg_holding_days: null
}

interface BacktestDetail {
  run_id: string
  type?: 'single' | 'batch'
  trades?: Trade[]
  daily_pnl?: DailyPnL[]
  metrics?: Metrics
  stocks?: any[]
  total_stocks?: number
  success_count?: number
  success_rate?: number
  total_trades?: number
  avg_return?: number
  avg_sharpe?: number
  avg_win_rate?: number
}

// Route and Router
const route = useRoute()
const router = useRouter()
const runId = computed(() => route.params.runId as string)

// State
const isLoading = ref(false)
const error = ref<string | null>(null)
const detail = ref<BacktestDetail | null>(null)

// Computed: is batch result
const isBatch = computed(() => detail.value?.type === 'batch')

// Pagination
const currentPage = ref(1)
const pageSize = ref(50)
const totalTrades = ref(0)

// Tab state
const activeTab = ref<'equity' | 'trades' | 'pnl' | 'drawdown'>('equity')

// Computed: paginated trades
const paginatedTrades = computed(() => {
  if (!detail.value?.trades) return []
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return detail.value.trades.slice(start, end)
})

const totalPages = computed(() => Math.ceil(totalTrades.value / pageSize.value))

// Watch for page changes
watch(() => detail.value?.trades, (newTrades) => {
  if (newTrades) {
    totalTrades.value = newTrades.length
    if (currentPage.value > totalPages.value) {
      currentPage.value = 1
    }
  }
})

// Fetch backtest detail
async function fetchDetail() {
  if (!runId.value) return
  
  isLoading.value = true
  error.value = null
  
  try {
    const response = await axios.get(`/api/backtest/${runId.value}`)
    detail.value = response.data
    
    // Also fetch trades for pagination info
    const tradesResponse = await axios.get(`/api/backtest/${runId.value}/trades`)
    if (tradesResponse.data.trades) {
      totalTrades.value = tradesResponse.data.trades.length
    }
  } catch (e: any) {
    error.value = '加载回测详情失败'
    console.error('Failed to fetch backtest detail:', e)
  } finally {
    isLoading.value = false
  }
}

// Equity Chart Data
const equityChartData = computed(() => {
  if (!detail.value?.daily_pnl?.length) {
    return { labels: [], datasets: [] }
  }
  
  return {
    labels: detail.value.daily_pnl.map(d => d.date),
    datasets: [
      {
        label: '策略收益',
        data: detail.value.daily_pnl.map(d => d.cumulative_return * 100),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        borderWidth: 2
      },
      {
        label: '基准收益',
        data: detail.value.daily_pnl.map(d => d.benchmark_return * 100),
        borderColor: '#64748b',
        borderDash: [5, 5],
        fill: false,
        tension: 0,
        pointRadius: 0,
        borderWidth: 1
      }
    ]
  }
})

const equityChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      labels: { color: '#94a3b8' }
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
      backgroundColor: '#1e293b',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      callbacks: {
        label: (context: any) => {
          return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`
        }
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b', maxTicksLimit: 8 }
    },
    y: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { 
        color: '#64748b',
        callback: (value: any) => Number(value).toFixed(1) + '%'
      }
    }
  },
  interaction: {
    mode: 'nearest' as const,
    axis: 'x' as const,
    intersect: false
  }
}

// Daily PnL Chart Data
const dailyPnLChartData = computed(() => {
  if (!detail.value?.daily_pnl?.length) {
    return { labels: [], datasets: [] }
  }
  
  const data = detail.value.daily_pnl.map(d => d.daily_pnl)
  
  return {
    labels: detail.value.daily_pnl.map(d => d.date),
    datasets: [{
      label: '每日盈亏',
      data: data,
      backgroundColor: data.map(v => v >= 0 ? 'rgba(239, 68, 68, 0.7)' : 'rgba(16, 185, 129, 0.7)'),
      borderWidth: 0,
      borderRadius: 2
    }]
  }
})

const dailyPnLChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1e293b',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      callbacks: {
        label: (context: any) => {
          const value = context.parsed.y
          const sign = value >= 0 ? '+' : ''
          return `${sign}${value.toFixed(2)}`
        }
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b', maxTicksLimit: 8 }
    },
    y: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { 
        color: '#64748b',
        callback: (value: any) => {
          const num = Number(value)
          const sign = num >= 0 ? '+' : ''
          return sign + num.toFixed(0)
        }
      }
    }
  }
}

// Drawdown Chart Data
const drawdownChartData = computed(() => {
  if (!detail.value?.daily_pnl?.length) {
    return { labels: [], datasets: [] }
  }
  
  return {
    labels: detail.value.daily_pnl.map(d => d.date),
    datasets: [{
      label: '回撤',
      data: detail.value.daily_pnl.map(d => d.drawdown * 100),
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239, 68, 68, 0.2)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      borderWidth: 2
    }]
  }
})

const drawdownChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1e293b',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      callbacks: {
        label: (context: any) => `回撤: ${Number(context.parsed.y).toFixed(2)}%`
      }
    }
  },
  scales: {
    x: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64748b', maxTicksLimit: 8 }
    },
    y: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { 
        color: '#64748b',
        callback: (value: any) => Number(value).toFixed(1) + '%'
      }
    }
  }
}

// Format helpers
function formatValue(value: number | undefined | null, decimals = 2): string {
  if (value === undefined || value === null) return '--'
  return value.toFixed(decimals)
}

function formatPercent(value: number | undefined | null): string {
  if (value === undefined || value === null) return '--'
  return (value * 100).toFixed(2) + '%'
}

function goBack() {
  router.push('/backtest-history')
}

// Lifecycle
onMounted(() => {
  fetchDetail()
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <header class="mb-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <button 
              @click="goBack"
              class="p-2 hover:bg-slate-700 rounded-lg transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div>
              <h1 class="text-2xl font-bold tracking-tight">回测详情</h1>
              <p v-if="detail" class="text-slate-400 text-sm mt-1">
                运行ID: {{ detail.run_id }}
              </p>
            </div>
          </div>
          
          <div v-if="isLoading" class="flex items-center gap-2 text-blue-400">
            <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span class="text-sm">加载中...</span>
          </div>
        </div>
      </header>

      <!-- Error State -->
      <div v-if="error" class="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-400">
        {{ error }}
      </div>

      <!-- Loading State -->
      <div v-if="isLoading && !detail" class="flex items-center justify-center py-20">
        <svg class="w-10 h-10 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <!-- Content -->
      <div v-if="detail && (detail.metrics || detail.type === 'batch')">
        <!-- Batch Result Metrics -->
        <div v-if="isBatch" class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">总股票数</p>
            <p class="text-xl font-bold text-slate-300">{{ detail.total_stocks || 0 }}</p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">成功</p>
            <p class="text-xl font-bold text-green-400">{{ detail.success_count || 0 }}</p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">成功率</p>
            <p class="text-xl font-bold text-blue-400">{{ formatPercent(detail.success_rate || 0) }}</p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">总交易次数</p>
            <p class="text-xl font-bold text-slate-300">{{ detail.total_trades || 0 }}</p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">平均收益率</p>
            <p :class="['text-xl font-bold', (detail.avg_return || 0) >= 0 ? 'text-red-400' : 'text-green-400']">
              {{ formatPercent(detail.avg_return || 0) }}
            </p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">平均夏普</p>
            <p class="text-xl font-bold text-blue-400">{{ formatValue(detail.avg_sharpe || 0) }}</p>
          </div>
        </div>

        <!-- Batch Stocks Table -->
        <div v-if="isBatch && detail.stocks?.length" class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl overflow-hidden mb-6">
          <div class="p-4 border-b border-slate-700">
            <h3 class="text-lg font-medium">股票回测结果 (前200)</h3>
            <p class="text-slate-400 text-sm mt-1">共 {{ detail.stocks.length }} 只股票</p>
          </div>
          <div class="overflow-x-auto max-h-96">
            <table class="w-full">
              <thead class="sticky top-0 bg-slate-800">
                <tr class="text-slate-400 text-sm border-b border-slate-700">
                  <th class="text-left py-3 px-4">代码</th>
                  <th class="text-left py-3 px-4">名称</th>
                  <th class="text-center py-3 px-4">状态</th>
                  <th class="text-right py-3 px-4">收益率</th>
                  <th class="text-right py-3 px-4">夏普</th>
                  <th class="text-right py-3 px-4">交易</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="stock in detail.stocks.slice(0, 200)" :key="stock.stock_code" class="border-b border-slate-800 hover:bg-slate-700/30">
                  <td class="py-3 px-4 text-slate-300">{{ stock.stock_code }}</td>
                  <td class="py-3 px-4 text-slate-300">{{ stock.stock_name }}</td>
                  <td class="py-3 px-4 text-center">
                    <span v-if="stock.status === 'success'" class="px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">成功</span>
                    <span v-else-if="stock.status === 'no_data'" class="px-2 py-0.5 bg-slate-500/20 text-slate-400 rounded text-xs">无数据</span>
                    <span v-else class="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-xs">失败</span>
                  </td>
                  <td :class="['py-3 px-4 text-right font-medium', (stock.total_return || 0) >= 0 ? 'text-red-400' : 'text-green-400']">
                    {{ formatPercent(stock.total_return || 0) }}
                  </td>
                  <td class="py-3 px-4 text-right text-slate-300">{{ formatValue(stock.sharpe_ratio || 0) }}</td>
                  <td class="py-3 px-4 text-right text-slate-300">{{ stock.total_trades || 0 }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Full Metrics Display for Batch Mode -->
        <div v-if="isBatch && detail.metrics" class="space-y-6">
          <!-- 收益类 -->
          <div>
            <h3 class="text-sm font-medium text-slate-400 mb-3">收益类</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">总盈亏</p>
                <p :class="['text-xl font-bold', (detail.metrics.total_profit ?? 0) >= 0 ? 'text-red-400' : 'text-green-400']">
                  {{ detail.metrics.total_profit != null ? '¥' + formatValue(detail.metrics.total_profit) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">累计收益率</p>
                <p :class="['text-xl font-bold', (detail.metrics.cumulative_return ?? 0) >= 0 ? 'text-red-400' : 'text-green-400']">
                  {{ detail.metrics.cumulative_return != null ? formatPercent(detail.metrics.cumulative_return) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">年化收益</p>
                <p :class="['text-xl font-bold', (detail.metrics.annualized_return ?? 0) >= 0 ? 'text-red-400' : 'text-green-400']">
                  {{ detail.metrics.annualized_return != null ? formatPercent(detail.metrics.annualized_return) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">期望值</p>
                <p :class="['text-xl font-bold', (detail.metrics.expectancy ?? 0) >= 0 ? 'text-red-400' : 'text-green-400']">
                  {{ detail.metrics.expectancy != null ? formatPercent(detail.metrics.expectancy) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">盈亏比</p>
                <p class="text-xl font-bold text-slate-300">
                  {{ detail.metrics.profit_loss_ratio != null ? formatValue(detail.metrics.profit_loss_ratio) : '--' }}
                  <span v-if="detail.metrics.profit_loss_ratio != null" class="text-xs text-slate-500 ml-1">(估算)</span>
                </p>
              </div>
            </div>
          </div>

          <!-- 风险类 -->
          <div>
            <h3 class="text-sm font-medium text-slate-400 mb-3">风险类</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">最大回撤</p>
                <p class="text-xl font-bold text-emerald-400">
                  {{ detail.metrics.max_drawdown != null ? formatPercent(detail.metrics.max_drawdown) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">平均回撤</p>
                <p class="text-xl font-bold text-emerald-400">
                  {{ detail.metrics.avg_drawdown != null ? formatPercent(detail.metrics.avg_drawdown) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">年化波动</p>
                <p class="text-xl font-bold text-slate-300">
                  {{ detail.metrics.volatility != null ? formatPercent(detail.metrics.volatility) : '--' }}
                  <span v-if="detail.metrics.volatility != null" class="text-xs text-slate-500 ml-1">(估算)</span>
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">胜率</p>
                <p class="text-xl font-bold text-slate-300">
                  {{ detail.metrics.win_rate != null ? formatPercent(detail.metrics.win_rate) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">总交易次数</p>
                <p class="text-xl font-bold text-slate-300">
                  {{ detail.metrics.total_trades != null ? detail.metrics.total_trades : '--' }}
                </p>
              </div>
            </div>
          </div>

          <!-- 比率类 -->
          <div>
            <h3 class="text-sm font-medium text-slate-400 mb-3">比率类</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">夏普比率</p>
                <p class="text-xl font-bold text-blue-400">
                  {{ detail.metrics.sharpe_ratio != null ? formatValue(detail.metrics.sharpe_ratio) : '--' }}
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">索提诺</p>
                <p class="text-xl font-bold text-blue-400">
                  {{ detail.metrics.sortino_ratio != null ? formatValue(detail.metrics.sortino_ratio) : '--' }}
                  <span v-if="detail.metrics.sortino_ratio != null" class="text-xs text-slate-500 ml-1">(估算)</span>
                </p>
              </div>
              <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
                <p class="text-slate-400 text-xs mb-1">卡玛比率</p>
                <p class="text-xl font-bold text-slate-300">
                  {{ detail.metrics.calmar_ratio != null ? formatValue(detail.metrics.calmar_ratio) : '--' }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Single Backtest Metrics -->
        <div v-if="!isBatch">
        <!-- Metrics Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">总收益率</p>
            <p :class="[
              'text-xl font-bold',
              (detail.metrics?.total_return || 0) >= 0 ? 'text-red-400' : 'text-green-400'
            ]">
              {{ formatPercent(detail.metrics?.total_return || 0) }}
            </p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">年化收益率</p>
            <p :class="[
              'text-xl font-bold',
              (detail.metrics?.annualized_return || 0) >= 0 ? 'text-red-400' : 'text-green-400'
            ]">
              {{ formatPercent(detail.metrics?.annualized_return || 0) }}
            </p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">夏普比率</p>
            <p class="text-xl font-bold text-blue-400">
              {{ formatValue(detail.metrics?.sharpe_ratio || 0) }}
            </p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">最大回撤</p>
            <p class="text-xl font-bold text-red-400">
              {{ formatPercent(detail.metrics?.max_drawdown || 0) }}
            </p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">胜率</p>
            <p class="text-xl font-bold text-purple-400">
              {{ formatPercent(detail.metrics?.win_rate || 0) }}
            </p>
          </div>
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-4">
            <p class="text-slate-400 text-xs mb-1">交易次数</p>
            <p class="text-xl font-bold text-slate-300">
              {{ detail.metrics?.total_trades || 0 }}
            </p>
          </div>
        </div>
        </div>

        <!-- Tabs -->
        <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl overflow-hidden">
          <div class="flex border-b border-slate-700">
            <button
              v-for="tab in [
                { key: 'equity', label: '收益曲线' },
                { key: 'trades', label: '交易记录' },
                { key: 'pnl', label: '每日盈亏' },
                { key: 'drawdown', label: '回撤' }
              ]"
              :key="tab.key"
              @click="activeTab = tab.key as any"
              :class="[
                'px-6 py-3 text-sm font-medium transition-colors',
                activeTab === tab.key
                  ? 'text-blue-400 border-b-2 border-blue-400 bg-slate-700/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/20'
              ]"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="p-6">
            <!-- Equity Curve Tab -->
            <div v-show="activeTab === 'equity'" class="h-80">
              <Line :data="equityChartData" :options="equityChartOptions" />
            </div>

            <!-- Trades Tab -->
            <div v-show="activeTab === 'trades'">
              <div class="overflow-x-auto">
                <table class="w-full">
                  <thead>
                    <tr class="text-slate-400 text-sm border-b border-slate-700">
                      <th class="text-left py-3 px-3">日期</th>
                      <th class="text-left py-3 px-3">股票</th>
                      <th class="text-center py-3 px-3">买卖</th>
                      <th class="text-right py-3 px-3">价格</th>
                      <th class="text-right py-3 px-3">数量</th>
                      <th class="text-right py-3 px-3">金额</th>
                      <th class="text-left py-3 px-3">信号</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr 
                      v-for="trade in paginatedTrades" 
                      :key="trade.id"
                      class="border-b border-slate-800 hover:bg-slate-700/30 transition-colors"
                    >
                      <td class="py-3 px-3 text-slate-300">{{ trade.date }}</td>
                      <td class="py-3 px-3">
                        <div class="flex items-center gap-2">
                          <span class="font-medium">{{ trade.name || '--' }}</span>
                          <span class="text-slate-500 text-sm">{{ trade.code }}</span>
                        </div>
                      </td>
                      <td class="py-3 px-3 text-center">
                        <span :class="[
                          'px-2 py-1 rounded text-xs font-medium',
                          trade.action?.toLowerCase().includes('buy') 
                            ? 'bg-red-500/20 text-red-400' 
                            : 'bg-green-500/20 text-green-400'
                        ]">
                          {{ trade.action }}
                        </span>
                      </td>
                      <td class="py-3 px-3 text-right text-slate-300">{{ formatValue(trade.price) }}</td>
                      <td class="py-3 px-3 text-right text-slate-300">{{ trade.volume }}</td>
                      <td class="py-3 px-3 text-right" :class="trade.amount >= 0 ? 'text-red-400' : 'text-green-400'">
                        {{ formatValue(trade.amount) }}
                      </td>
                      <td class="py-3 px-3 text-slate-400 text-sm">{{ trade.signal_type || '--' }}</td>
                    </tr>
                    <tr v-if="paginatedTrades.length === 0">
                      <td colspan="7" class="text-center py-8 text-slate-400">暂无交易记录</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Pagination -->
              <div v-if="totalPages > 1" class="flex items-center justify-between mt-4 pt-4 border-t border-slate-700">
                <p class="text-sm text-slate-400">
                  共 {{ totalTrades }} 条记录，第 {{ currentPage }}/{{ totalPages }} 页
                </p>
                <div class="flex gap-2">
                  <button
                    @click="currentPage = 1"
                    :disabled="currentPage === 1"
                    class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 rounded text-sm transition-colors"
                  >
                    首页
                  </button>
                  <button
                    @click="currentPage--"
                    :disabled="currentPage === 1"
                    class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 rounded text-sm transition-colors"
                  >
                    上一页
                  </button>
                  <button
                    @click="currentPage++"
                    :disabled="currentPage === totalPages"
                    class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 rounded text-sm transition-colors"
                  >
                    下一页
                  </button>
                  <button
                    @click="currentPage = totalPages"
                    :disabled="currentPage === totalPages"
                    class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 rounded text-sm transition-colors"
                  >
                    末页
                  </button>
                </div>
              </div>
            </div>

            <!-- Daily PnL Tab -->
            <div v-show="activeTab === 'pnl'" class="h-80">
              <Bar :data="dailyPnLChartData" :options="dailyPnLChartOptions" />
            </div>

            <!-- Drawdown Tab -->
            <div v-show="activeTab === 'drawdown'" class="h-80">
              <Line :data="drawdownChartData" :options="drawdownChartOptions" />
            </div>
          </div>
        </div>
        </div>

      <!-- Empty State -->
      <div v-if="!isLoading && !detail" class="flex flex-col items-center justify-center py-20">
        <svg class="w-16 h-16 text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p class="text-slate-400">未找到回测详情</p>
        <button 
          @click="goBack"
          class="mt-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 rounded-lg text-sm transition-colors"
        >
          返回历史
        </button>
      </div>
    </div>
  </div>
</template>
