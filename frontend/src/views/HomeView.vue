<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import ChartDataLabels from 'chartjs-plugin-annotation'
import PositionsView from './PositionsView.vue'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler, ChartDataLabels)

interface Stats {
  today_buy_signals?: number
  latest_date?: string
}

interface PositionSummary {
  total_value?: number
  available_cash?: number
  total_profit?: number
  count?: number
}

const stats = ref<Stats>({})
const positionSummary = ref<PositionSummary>({})
const loading = ref(true)

// Equity Curve
const equityCurveData = ref<any>(null)
const equityCurveLoading = ref(true)

// Signals
const signals = ref<any>(null)
const signalsLoading = ref(true)
const signalTab = ref<'buy' | 'sell'>('buy')

// Signal filtering
const buySignals = computed(() => 
  (signals.value?.signals || []).filter((s: any) => s.buy_signals?.length > 0)
)
const sellSignals = computed(() =>
  (signals.value?.signals || []).filter((s: any) => s.sell_signals?.length > 0)
)

const getSignalList = (signal: any) =>
  signalTab.value === 'buy' ? signal.buy_signals : signal.sell_signals

// Strategy Comparison
const strategyData = ref<any>(null)
const strategyLoading = ref(true)

// History
const historyData = ref<any>(null)
const historyLoading = ref(true)

// Positions
const positionsData = ref<any[]>([])
const positionsSummary = ref<any>({})
const positionsLoading = ref(true)

const fetchData = async () => {
  try {
    const [statsRes, positionsRes] = await Promise.all([
      axios.get('/api/stats'),
      axios.get('/api/positions')
    ])
    stats.value = statsRes.data || {}
    positionSummary.value = positionsRes.data.summary || {}
  } catch (e) {
    console.error('Failed to fetch data:', e)
  } finally {
    loading.value = false
  }
}

const fetchEquityCurve = async () => {
  try {
    const res = await axios.get('/api/equity-curve')
    equityCurveData.value = res.data
  } catch (e) {
    console.error('Failed to fetch equity curve:', e)
  } finally {
    equityCurveLoading.value = false
  }
}

const fetchSignals = async () => {
  try {
    signalsLoading.value = true
    const res = await axios.get('/api/signals')
    signals.value = res.data || []
  } catch (e) {
    console.error('Failed to fetch signals:', e)
  } finally {
    signalsLoading.value = false
  }
}

const fetchStrategyComparison = async () => {
  try {
    const res = await axios.get('/api/strategy-comparison')
    strategyData.value = res.data
  } catch (e) {
    console.error('Failed to fetch strategy comparison:', e)
  } finally {
    strategyLoading.value = false
  }
}

const fetchHistory = async () => {
  try {
    const res = await axios.get('/api/history')
    historyData.value = res.data
  } catch (e) {
    console.error('Failed to fetch history:', e)
  } finally {
    historyLoading.value = false
  }
}

const fetchPositionsData = async () => {
  try {
    positionsLoading.value = true
    const response = await axios.get('/api/positions')
    positionsData.value = response.data.positions || []
    positionsSummary.value = response.data.summary || {}
  } catch (e) {
    console.error('Failed to fetch positions:', e)
  } finally {
    positionsLoading.value = false
  }
}

const formatMoney = (value: number | undefined) => {
  if (value === null || value === undefined) return '--'
  const absValue = Math.abs(value)
  if (absValue >= 10000) {
    return (value >= 0 ? '+' : '') + (value / 10000).toFixed(2) + '万'
  }
  return (value >= 0 ? '+' : '') + value.toFixed(2)
}

// Equity Curve Chart
const equityChartData = computed(() => {
  if (!equityCurveData.value) return null
  
  const { dates, values, benchmark } = equityCurveData.value
  
  return {
    labels: dates,
    datasets: [
      {
        label: '策略',
        data: values,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: '#3b82f6'
      },
      {
        label: '基准',
        data: benchmark,
        borderColor: '#64748b',
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        borderDash: [5, 5],
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 4
      }
    ]
  }
})

const equityChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  height: 400 as number,
  interaction: {
    mode: 'index' as const,
    intersect: false
  },
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
      labels: {
        color: '#94a3b8',
        usePointStyle: true,
        padding: 20
      }
    },
    tooltip: {
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      padding: 12,
      callbacks: {
        label: (context: any) => {
          const label = context.dataset.label || ''
          const value = context.parsed.y
          return `${label}: ${value.toLocaleString()}`
        },
        afterLabel: (context: any) => {
          if (context.datasetIndex === 0 && equityCurveData.value && equityCurveData.value.values && equityCurveData.value.values.length > 0) {
            const idx = context.dataIndex
            const data = equityCurveData.value
            return `持仓收益: ${(data.values[idx] - data.values[0]).toFixed(2)}`
          }
          return ''
        }
      }
    },
    annotation: {
      annotations: equityCurveData.value ? {
        peak: {
          type: 'point' as const,
          xValue: equityCurveData.value.annotations.peak.date,
          yValue: equityCurveData.value.annotations.peak.value,
          backgroundColor: '#10b981',
          borderColor: '#10b981',
          radius: 6,
          label: {
            display: true,
            content: '峰值',
            color: '#10b981',
            position: 'start',
            backgroundColor: 'transparent',
            font: { size: 12 }
          }
        },
        maxdd: {
          type: 'point' as const,
          xValue: equityCurveData.value.annotations.max_drawdown.date,
          yValue: equityCurveData.value.annotations.max_drawdown.value,
          backgroundColor: '#ef4444',
          borderColor: '#ef4444',
          radius: 6,
          label: {
            display: true,
            content: `最大回撤${(equityCurveData.value.annotations.max_drawdown.drawdown * 100).toFixed(1)}%`,
            color: '#ef4444',
            position: 'start',
            backgroundColor: 'transparent',
            font: { size: 12 }
          }
        }
      } : {}
    }
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(51, 65, 85, 0.5)',
        drawBorder: false
      },
      ticks: {
        color: '#64748b',
        maxTicksLimit: 8
      }
    },
    y: {
      grid: {
        color: 'rgba(51, 65, 85, 0.5)',
        drawBorder: false
      },
      ticks: {
        color: '#64748b',
        callback: (value: any) => value.toLocaleString()
      }
    }
  }
}))

// Strategy Comparison Chart
const strategyChartData = computed(() => {
  if (!strategyData.value) return null
  
  const { dates, initial_value, curves } = strategyData.value
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
  
  const datasets = Object.entries(curves || {}).map(([name, curveData]: [string, any], idx: number) => ({
    label: name,
    data: (curveData.data || []).map((v: number) => ((v / initial_value) - 1) * 100),
    borderColor: curveData.color || colors[idx % colors.length],
    backgroundColor: 'transparent',
    borderWidth: 2,
    fill: false,
    tension: 0.4,
    pointRadius: 0,
    pointHoverRadius: 4
  }))
  
  return {
    labels: dates,
    datasets
  }
})

const strategyChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  height: 350 as number,
  interaction: {
    mode: 'index' as const,
    intersect: false
  },
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
      align: 'end' as const,
      labels: {
        color: '#94a3b8',
        usePointStyle: true,
        padding: 15,
        font: { size: 11 }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(30, 41, 59, 0.95)',
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
      borderColor: '#334155',
      borderWidth: 1,
      padding: 12,
      callbacks: {
        label: (context: any) => {
          const label = context.dataset.label || ''
          const value = context.parsed.y
          return `${label}: ${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        color: 'rgba(51, 65, 85, 0.5)',
        drawBorder: false
      },
      ticks: {
        color: '#64748b',
        maxTicksLimit: 8
      }
    },
    y: {
      grid: {
        color: 'rgba(51, 65, 85, 0.5)',
        drawBorder: false
      },
      ticks: {
        color: '#64748b',
        callback: (value: any) => `${value}%`
      }
    }
  }
}))

// History computed
const historyTrades = computed(() => historyData.value?.history || [])
const historyStats = computed(() => {
  const trades = historyTrades.value as any[]
  const total_trades = trades.length
  const total_profit = trades.reduce((sum: number, t: any) => sum + (t.profit_loss || 0), 0)
  const winning_trades = trades.filter((t: any) => (t.profit_loss || 0) > 0).length
  const win_rate = total_trades > 0 ? winning_trades / total_trades : 0
  const win_total = trades.filter((t: any) => (t.profit_loss || 0) > 0).reduce((sum: number, t: any) => sum + (t.profit_loss || 0), 0)
  const loss_total = Math.abs(trades.filter((t: any) => (t.profit_loss || 0) < 0).reduce((sum: number, t: any) => sum + (t.profit_loss || 0), 0))
  const avg_win = winning_trades > 0 ? win_total / winning_trades : 0
  const avg_loss = (total_trades - winning_trades) > 0 ? loss_total / (total_trades - winning_trades) : 0
  const profit_loss_ratio = avg_loss > 0 ? avg_win / avg_loss : 0
  return { total_trades, total_profit, win_rate, profit_loss_ratio }
})

// Format date
const formatDate = (dateStr: string) => {
  if (!dateStr) return '--'
  return dateStr
}

onMounted(() => {
  fetchData()
  fetchEquityCurve()
  fetchSignals()
  fetchStrategyComparison()
  fetchHistory()
  fetchPositionsData()
})
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <!-- Stats Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="glass-card p-4 animate-fade-in" style="animation-delay: 0.1s">
        <p class="text-slate-400 text-sm mb-1">持仓金额</p>
        <p class="text-2xl font-bold">{{ formatMoney(positionSummary.total_value) }}</p>
      </div>
      <div class="glass-card p-4 animate-fade-in" style="animation-delay: 0.2s">
        <p class="text-slate-400 text-sm mb-1">可用资金</p>
        <p class="text-2xl font-bold">{{ formatMoney(positionSummary.available_cash) }}</p>
      </div>
      <div class="glass-card p-4 animate-fade-in" style="animation-delay: 0.3s">
        <p class="text-slate-400 text-sm mb-1">总盈亏</p>
        <p class="text-2xl font-bold" :class="(positionSummary.total_profit || 0) >= 0 ? 'profit-positive' : 'profit-negative'">
          {{ formatMoney(positionSummary.total_profit) }}
        </p>
      </div>
      <div class="glass-card p-4 animate-fade-in" style="animation-delay: 0.4s">
        <p class="text-slate-400 text-sm mb-1">盈亏比</p>
        <p class="text-2xl font-bold" :class="(historyStats.profit_loss_ratio || 0) >= 1 ? 'profit-positive' : 'profit-negative'">
          {{ (historyStats.profit_loss_ratio || 0).toFixed(2) }}
        </p>
      </div>
    </div>

    <!-- Equity Curve + Signals Panel (side-by-side) -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <!-- Equity Curve Chart -->
      <div class="glass-card p-4 animate-fade-in lg:col-span-8" style="animation-delay: 0.5s">
        <h3 class="text-lg font-semibold text-slate-100 mb-4">权益曲线</h3>
        <div v-if="equityCurveLoading" class="h-96 flex items-center justify-center text-slate-400">
          加载中...
        </div>
        <div v-else-if="!equityChartData" class="h-96 flex items-center justify-center text-slate-400">
          暂无数据
        </div>
        <div v-else class="h-[400px]">
          <Line :data="equityChartData" :options="equityChartOptions" />
        </div>
      </div>

      <!-- Signals Panel -->
      <div class="glass-card p-4 animate-fade-in lg:col-span-4" style="animation-delay: 0.5s">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
            <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-slate-100">今日信号</h3>
        </div>

        <!-- Tab Buttons -->
        <div class="flex gap-2 mb-4">
          <button
            @click="signalTab = 'buy'"
            :class="signalTab === 'buy' ? 'bg-red-900/50 text-red-400 border border-red-700' : 'bg-slate-800/50 text-slate-400 border border-slate-700'"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            买入信号 ({{ buySignals.length }})
          </button>
          <button
            @click="signalTab = 'sell'"
            :class="signalTab === 'sell' ? 'bg-green-900/50 text-green-400 border border-green-700' : 'bg-slate-800/50 text-slate-400 border border-slate-700'"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            卖出信号 ({{ sellSignals.length }})
          </button>
        </div>

        <!-- Signal List (vertical) -->
        <div class="space-y-2 overflow-y-auto max-h-[400px]">
          <div
            v-for="signal in (signalTab === 'buy' ? buySignals : sellSignals)"
            :key="signal.code"
            class="p-3 rounded-lg border transition-colors"
            :class="signalTab === 'buy' ? 'bg-red-500/10 border-red-500/20' : 'bg-green-500/10 border-green-500/20'"
          >
            <div class="flex items-center justify-between mb-2">
              <div>
                <span class="text-slate-100 font-medium">{{ signal.name }}</span>
                <span class="text-slate-500 text-xs ml-2">{{ signal.code }}</span>
              </div>
              <span class="text-slate-100 font-semibold">¥{{ (signal.close || 0).toFixed(2) }}</span>
            </div>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="sig in getSignalList(signal)"
                :key="sig.strategy"
                class="px-2 py-0.5 rounded text-xs font-medium"
                :class="signalTab === 'buy' ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'"
              >
                {{ sig.strategy }} {{ sig.score.toFixed(1) }}分
              </span>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="(signalTab === 'buy' ? buySignals : sellSignals).length === 0" class="text-center py-8 text-slate-400">
          暂无{{ signalTab === 'buy' ? '买入' : '卖出' }}信号
        </div>
      </div>
    </div>

    <!-- Strategy Comparison Chart -->
    <div class="glass-card p-4 mb-6 mt-6 animate-fade-in" style="animation-delay: 0.6s">
      <h3 class="text-lg font-semibold text-slate-100 mb-4">策略对比</h3>
      <div v-if="strategyLoading" class="h-80 flex items-center justify-center text-slate-400">
        加载中...
      </div>
      <div v-else-if="!strategyChartData" class="h-80 flex items-center justify-center text-slate-400">
        暂无数据
      </div>
      <div v-else class="h-[350px]">
        <Line :data="strategyChartData" :options="strategyChartOptions" />
      </div>
    </div>

    <!-- 持仓模块 -->
    <PositionsView embedded class="mb-6 animate-fade-in" style="animation-delay: 0.65s" />

    <!-- History Trades Table -->
    <div class="glass-card p-4 mb-6 animate-fade-in" style="animation-delay: 0.7s">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-slate-100">历史交易</h3>
        <router-link 
          to="/history-analysis" 
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm font-medium transition-colors"
        >
          查看分析
        </router-link>
      </div>
      
      <!-- Stats Cards -->
      <div v-if="historyData" class="grid grid-cols-3 gap-4 mb-4">
        <div class="bg-slate-800/50 rounded-lg p-3 text-center">
          <p class="text-slate-400 text-xs mb-1">总交易次数</p>
          <p class="text-xl font-bold text-slate-100">{{ historyStats.total_trades }}</p>
        </div>
        <div class="bg-slate-800/50 rounded-lg p-3 text-center">
          <p class="text-slate-400 text-xs mb-1">总盈亏</p>
          <p 
            class="text-xl font-bold"
            :class="historyStats.total_profit >= 0 ? 'text-red-400' : 'text-green-400'"
          >
            {{ formatMoney(historyStats.total_profit) }}
          </p>
        </div>
        <div class="bg-slate-800/50 rounded-lg p-3 text-center">
          <p class="text-slate-400 text-xs mb-1">胜率</p>
          <p class="text-xl font-bold text-slate-100">           {{ ((historyStats.win_rate || 0) * 100).toFixed(1) }}%</p>
        </div>
      </div>
      
      <!-- Table -->
      <div v-if="historyLoading" class="text-center py-8 text-slate-400">
        加载中...
      </div>
      <div v-else-if="!historyData || historyTrades.length === 0" class="text-center py-8 text-slate-400">
        暂无历史交易
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-700">
              <th class="text-left py-3 px-2 text-slate-400 font-medium">股票</th>
              <th class="text-left py-3 px-2 text-slate-400 font-medium">买入日期</th>
              <th class="text-right py-3 px-2 text-slate-400 font-medium">买入价</th>
              <th class="text-left py-3 px-2 text-slate-400 font-medium">卖出日期</th>
              <th class="text-right py-3 px-2 text-slate-400 font-medium">卖出价</th>
              <th class="text-left py-3 px-2 text-slate-400 font-medium">卖出原因</th>
              <th class="text-right py-3 px-2 text-slate-400 font-medium">盈亏</th>
              <th class="text-right py-3 px-2 text-slate-400 font-medium">盈亏%</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="trade in historyTrades" 
              :key="trade.code + trade.buy_date"
              class="border-b border-slate-800 hover:bg-slate-800/30"
            >
              <td class="py-3 px-2">
                <div class="text-slate-100">{{ trade.name }}</div>
                <div class="text-slate-400 text-xs">{{ trade.code }}</div>
                <div class="flex gap-2 mt-1 text-xs">
                  <span class="text-red-400">买: {{ trade.buy_signal_type || '趋势择时' }}</span>
                  <span class="text-green-400">卖: {{ trade.sell_signal_type || '信号卖出' }}</span>
                </div>
              </td>
              <td class="py-3 px-2 text-slate-300">{{ formatDate(trade.buy_date) }}</td>
              <td class="py-3 px-2 text-right text-slate-300">{{ (trade.buy_price || 0).toFixed(2) }}</td>
              <td class="py-3 px-2 text-slate-300">{{ formatDate(trade.sell_date) }}</td>
              <td class="py-3 px-2 text-right text-slate-300">{{ (trade.sell_price || 0).toFixed(2) }}</td>
              <td class="py-3 px-2 text-slate-400 text-xs">{{ trade.sell_reason }}</td>
              <td 
                class="py-3 px-2 text-right font-medium"
                :class="(trade.profit_loss || 0) >= 0 ? 'text-red-400' : 'text-green-400'"
              >
                {{ (trade.profit_loss || 0) >= 0 ? '+' : '' }}{{ (trade.profit_loss || 0).toFixed(2) }}
              </td>
              <td 
                class="py-3 px-2 text-right font-medium"
                :class="(trade.profit_pct || 0) >= 0 ? 'text-red-400' : 'text-green-400'"
              >
                {{ (trade.profit_pct || 0) >= 0 ? '+' : '' }}{{ (trade.profit_pct || 0).toFixed(2) }}%
              </td>
            </tr>
          </tbody>
        </table>
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

.profit-positive {
  color: #ef4444;
}

.profit-negative {
  color: #10b981;
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
