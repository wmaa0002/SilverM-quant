<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useBacktestStore } from '../stores/backtestStore'
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

const store = useBacktestStore()
const router = useRouter()

// Parameter sweep input
const paramGridInput = ref('')

// Tab switching: 'dashboard' or 'history'
const currentView = ref<'dashboard' | 'history'>('dashboard')

// 历史记录相关
interface BacktestRun {
  run_id: string
  type?: 'single' | 'batch'
  strategy_name: string
  start_date: string
  end_date: string
  initial_capital?: number
  status?: string
  completed_at?: string
  total_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
  total_stocks?: number
  success_count?: number
  success_rate?: number
  total_trades?: number
}

const historyRuns = ref<BacktestRun[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(10)
const historyPageSizeOptions = [10, 20, 50]
const filterStrategyName = ref('')
const filterStartDate = ref('')
const filterEndDate = ref('')
const sortColumn = ref<string>('completed_at')
const sortOrder = ref<'asc' | 'desc'>('desc')
const isHistoryLoading = ref(false)

const historyTotalPages = computed(() => Math.ceil(historyTotal.value / historyPageSize.value))

async function fetchHistory() {
  isHistoryLoading.value = true
  try {
    const params: Record<string, any> = {
      page: historyPage.value,
      limit: historyPageSize.value
    }
    if (filterStrategyName.value) {
      params.strategy_name = filterStrategyName.value
    }
    if (filterStartDate.value) {
      params.start_date = filterStartDate.value
    }
    if (filterEndDate.value) {
      params.end_date = filterEndDate.value
    }

    const response = await axios.get('/api/backtest/history', { params })
    historyRuns.value = response.data.runs || []
    historyTotal.value = response.data.total || 0
  } catch (e) {
    console.error('Failed to fetch history:', e)
    historyRuns.value = []
    historyTotal.value = 0
  } finally {
    isHistoryLoading.value = false
  }
}

// 切换到历史视图时自动加载数据
watch(currentView, (newView) => {
  if (newView === 'history' && historyRuns.value.length === 0) {
    fetchHistory()
  }
})

function handleHistorySearch() {
  historyPage.value = 1
  fetchHistory()
}

function handleHistoryReset() {
  filterStrategyName.value = ''
  filterStartDate.value = ''
  filterEndDate.value = ''
  historyPage.value = 1
  fetchHistory()
}

function handleHistoryPageSizeChange(size: number) {
  historyPageSize.value = size
  historyPage.value = 1
  fetchHistory()
}

function handleHistoryPageChange(page: number) {
  historyPage.value = page
  fetchHistory()
}

function handleHistorySort(column: string) {
  if (sortColumn.value === column) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortOrder.value = 'desc'
  }
  fetchHistory()
}

function viewHistoryDetail(run: BacktestRun) {
  router.push({ name: 'backtest-detail', params: { runId: run.run_id } })
}

function formatHistoryDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  return dateStr
}

function formatHistoryNumber(num: number | undefined, decimals: number = 2): string {
  if (num === undefined || num === null) return '-'
  return num.toFixed(decimals)
}

function formatHistoryPercent(num: number | undefined): string {
  if (num === undefined || num === null) return '-'
  return (num * 100).toFixed(2) + '%'
}

function formatHistoryDateTime(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

function getHistorySortIcon(column: string): string {
  if (sortColumn.value !== column) return ''
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

const stockInput = ref('')
const showStrategyDropdown = ref(false)

onMounted(() => {
  store.fetchStrategies()
})

const filteredStrategies = computed(() => {
  if (!stockInput.value) return store.strategies
  const query = stockInput.value.toLowerCase()
  return store.strategies.filter(s => s.name.toLowerCase().includes(query))
})

function toggleStrategy(strategyName: string) {
  const idx = store.selectedStrategies.indexOf(strategyName)
  if (idx === -1) {
    store.selectedStrategies.push(strategyName)
  } else {
    store.selectedStrategies.splice(idx, 1)
  }
}

function removeStrategy(strategyName: string) {
  const idx = store.selectedStrategies.indexOf(strategyName)
  if (idx !== -1) {
    store.selectedStrategies.splice(idx, 1)
  }
}

function setStockMode(mode: 'all' | 'single' | 'multiple') {
  store.stockSelectionMode = mode
  if (mode === 'all') {
    store.selectedStocks = []
  }
}

function addStock() {
  if (stockInput.value && !store.selectedStocks.includes(stockInput.value)) {
    store.selectedStocks.push(stockInput.value)
    stockInput.value = ''
  }
}

function removeStock(stock: string) {
  const idx = store.selectedStocks.indexOf(stock)
  if (idx !== -1) {
    store.selectedStocks.splice(idx, 1)
  }
}

const equityChartData = computed(() => {
  if (!store.currentResult?.metrics) {
    return {
      labels: [],
      datasets: []
    }
  }
  return {
    labels: ['收益曲线'],
    datasets: [{
      label: '总收益率',
      data: [store.currentResult.metrics.total_return],
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4
    }]
  }
})

const equityChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      labels: {
        color: '#94a3b8'
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

const metricsChartData = computed(() => {
  if (!store.currentResult?.metrics) {
    return {
      labels: [],
      datasets: []
    }
  }
  const m = store.currentResult.metrics
  return {
    labels: ['夏普比率', '索提诺比率', '卡尔马比率', '胜率'],
    datasets: [{
      label: '指标值',
      data: [m.sharpe_ratio, m.sortino_ratio, m.calmar_ratio, m.win_rate * 100],
      backgroundColor: [
        'rgba(59, 130, 246, 0.7)',
        'rgba(16, 185, 129, 0.7)',
        'rgba(245, 158, 11, 0.7)',
        'rgba(139, 92, 246, 0.7)'
      ],
      borderWidth: 0
    }]
  }
})

const metricsChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: false
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#64748b' }
    },
    y: {
      grid: { color: 'rgba(51, 65, 85, 0.5)' },
      ticks: { color: '#64718b' }
    }
  }
}

// Per-Stock Breakdown
const stockFilter = ref('')
const stockSortKey = ref('total_return')
const stockSortOrder = ref<'asc' | 'desc'>('desc')

const filteredStocks = computed(() => {
  if (!store.batchResult?.stocks) return []
  let stocks = [...store.batchResult.stocks]

  if (stockFilter.value) {
    stocks = stocks.filter(s => s.status === stockFilter.value)
  }

  stocks.sort((a, b) => {
    const aVal = a[stockSortKey.value as keyof typeof a]
    const bVal = b[stockSortKey.value as keyof typeof b]
    if (aVal == null) return 1
    if (bVal == null) return -1
    if (stockSortOrder.value === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })

  return stocks
})

function sortStocks(key: string) {
  if (stockSortKey.value === key) {
    stockSortOrder.value = stockSortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    stockSortKey.value = key
    stockSortOrder.value = 'desc'
  }
}

const bestParamIndex = computed(() => {
  if (!store.batchResult?.param_results?.length) return -1
  let best = 0
  let bestReturn = -Infinity
  store.batchResult.param_results.forEach((pr: any, idx: number) => {
    if ((pr.results?.avg_return || 0) > bestReturn) {
      bestReturn = pr.results.avg_return
      best = idx
    }
  })
  return best
})

function getReturnClass(returnValue: number) {
  if (returnValue > 0) return 'text-red-400'
  if (returnValue < 0) return 'text-green-400'
  return 'text-slate-400'
}

function goToStrategyManagement() {
  router.push({ name: 'strategy-management' })
}

async function rescanStrategies() {
  try {
    await axios.post('/api/backtest/register-strategies')
    await store.fetchStrategies()
  } catch (e) {
    console.error('Failed to rescan strategies:', e)
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
    <div class="max-w-7xl mx-auto">
      <header class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold tracking-tight">回测 Dashboard</h1>
            <p class="text-slate-400 mt-1">选择策略并运行回测分析</p>
          </div>
          <div class="flex gap-2">
            <button
              @click="currentView = 'dashboard'"
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                currentView === 'dashboard'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              ]"
            >
              回测配置
            </button>
            <button
              @click="currentView = 'history'"
              :class="[
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                currentView === 'history'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              ]"
            >
              回测历史
            </button>
            <button
              @click="goToStrategyManagement"
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-slate-700 text-slate-300 hover:bg-slate-600"
            >
              策略管理
            </button>
          </div>
        </div>
      </header>

      <div v-if="currentView === 'dashboard'" class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 space-y-6">
          <!-- Batch Progress Card -->
          <div v-if="store.isBatchRunning" class="bg-slate-800/50 backdrop-blur border border-blue-500/50 rounded-xl p-6 mb-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold">批量回测进行中</h3>
              <span class="text-blue-400 text-sm">{{ store.batchProgress }}%</span>
            </div>
            <div class="w-full bg-slate-700 rounded-full h-2 mb-2">
              <div class="bg-blue-500 h-2 rounded-full transition-all" :style="{ width: store.batchProgress + '%' }"></div>
            </div>
            <p class="text-slate-400 text-sm">{{ store.batchMessage }}</p>
          </div>

          <!-- Batch Results Card -->
          <div v-if="store.hasBatchResult && store.batchResult" class="space-y-6">
            <!-- Stats Grid -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div class="bg-slate-800/50 rounded-lg p-4">
                <p class="text-slate-400 text-xs mb-1">成功</p>
                <p class="text-2xl font-bold text-green-400">{{ store.batchResult.success_count }}/{{ store.batchResult.total_stocks }}</p>
              </div>
              <div class="bg-slate-800/50 rounded-lg p-4">
                <p class="text-slate-400 text-xs mb-1">平均收益率</p>
                <p class="text-2xl font-bold" :class="store.batchResult.avg_return >= 0 ? 'text-red-400' : 'text-green-400'">
                  {{ (store.batchResult.avg_return * 100).toFixed(2) }}%
                </p>
              </div>
              <div class="bg-slate-800/50 rounded-lg p-4">
                <p class="text-slate-400 text-xs mb-1">平均夏普比率</p>
                <p class="text-2xl font-bold text-blue-400">{{ store.batchResult.avg_sharpe.toFixed(2) }}</p>
              </div>
              <div class="bg-slate-800/50 rounded-lg p-4">
                <p class="text-slate-400 text-xs mb-1">平均胜率</p>
                <p class="text-2xl font-bold text-purple-400">{{ (store.batchResult.avg_win_rate * 100).toFixed(1) }}%</p>
              </div>
            </div>

            <!-- Top5/Bottom5 -->
            <div class="grid grid-cols-2 gap-6">
              <div class="bg-slate-800/50 rounded-lg p-4">
                <h4 class="text-green-400 font-semibold mb-3">收益Top5</h4>
                <ul class="space-y-2">
                  <li v-for="stock in store.batchResult.top5_stocks" :key="stock.stock_code" class="flex justify-between text-sm">
                    <span>{{ stock.stock_code }} {{ stock.stock_name }}</span>
                    <span class="text-green-400">{{ (stock.total_return * 100).toFixed(2) }}%</span>
                  </li>
                </ul>
              </div>
              <div class="bg-slate-800/50 rounded-lg p-4">
                <h4 class="text-red-400 font-semibold mb-3">收益Bottom5</h4>
                <ul class="space-y-2">
                  <li v-for="stock in store.batchResult.bottom5_stocks" :key="stock.stock_code" class="flex justify-between text-sm">
                    <span>{{ stock.stock_code }} {{ stock.stock_name }}</span>
                    <span class="text-red-400">{{ (stock.total_return * 100).toFixed(2) }}%</span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Param Sweep Comparison -->
            <div v-if="store.batchResult?.param_results && store.batchResult.param_results.length > 0" class="mt-6">
              <h4 class="text-lg font-semibold mb-3">参数扫描对比</h4>
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="text-slate-400 border-b border-slate-700">
                      <th class="py-2 px-3 text-left">参数</th>
                      <th class="py-2 px-3 text-right">平均收益率</th>
                      <th class="py-2 px-3 text-right">夏普比率</th>
                      <th class="py-2 px-3 text-right">胜率</th>
                      <th class="py-2 px-3 text-right">交易次数</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(pr, idx) in store.batchResult.param_results" :key="idx"
                        class="border-b border-slate-800 hover:bg-slate-700/30"
                        :class="idx === bestParamIndex ? 'bg-green-900/20' : ''">
                      <td class="py-2 px-3">
                        {{ pr.param_name }}: {{ pr.param_values?.join(', ') }}
                        <span v-if="idx === bestParamIndex" class="ml-2 text-xs text-green-400">最佳</span>
                      </td>
                      <td class="py-2 px-3 text-right" :class="getReturnClass(pr.results?.avg_return)">
                        {{ ((pr.results?.avg_return || 0) * 100).toFixed(2) }}%
                      </td>
                      <td class="py-2 px-3 text-right text-blue-400">{{ (pr.results?.sharpe_ratio || 0).toFixed(2) }}</td>
                      <td class="py-2 px-3 text-right text-purple-400">{{ ((pr.results?.win_rate || 0) * 100).toFixed(1) }}%</td>
                      <td class="py-2 px-3 text-right">{{ pr.results?.total_trades || 0 }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- Per-Stock Breakdown -->
          <div v-if="store.batchResult?.stocks && store.batchResult.stocks.length > 0" class="mt-6">
            <div class="flex items-center justify-between mb-4">
              <h4 class="text-lg font-semibold">全部股票 ({{ store.batchResult?.stocks?.length }})</h4>
              <div class="flex gap-2">
                <select v-model="stockFilter" class="px-3 py-1 bg-slate-700 border border-slate-600 rounded text-sm">
                  <option value="">全部</option>
                  <option value="success">成功</option>
                  <option value="error">失败</option>
                  <option value="no_data">无数据</option>
                </select>
              </div>
            </div>

            <div class="overflow-x-auto max-h-96 overflow-y-auto">
              <table class="w-full text-sm">
                <thead class="sticky top-0 bg-slate-800">
                  <tr class="text-slate-400 border-b border-slate-700">
                    <th class="py-2 px-3 text-left cursor-pointer hover:text-white" @click="sortStocks('stock_code')">代码</th>
                    <th class="py-2 px-3 text-left">名称</th>
                    <th class="py-2 px-3 text-left">状态</th>
                    <th class="py-2 px-3 text-right cursor-pointer hover:text-white" @click="sortStocks('total_return')">收益率</th>
                    <th class="py-2 px-3 text-right">夏普</th>
                    <th class="py-2 px-3 text-right">胜率</th>
                    <th class="py-2 px-3 text-right">交易次数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="stock in filteredStocks" :key="stock.stock_code"
                      class="border-b border-slate-800 hover:bg-slate-700/30">
                    <td class="py-2 px-3 font-mono text-blue-400">{{ stock.stock_code }}</td>
                    <td class="py-2 px-3">{{ stock.stock_name || '-' }}</td>
                    <td class="py-2 px-3">
                      <span v-if="stock.status === 'success'" class="text-green-400">成功</span>
                      <span v-else-if="stock.status === 'no_data'" class="text-slate-500">无数据</span>
                      <span v-else class="text-red-400">失败</span>
                    </td>
                    <td class="py-2 px-3 text-right" :class="stock.total_return >= 0 ? 'text-red-400' : 'text-green-400'">
                      {{ stock.total_return != null ? (stock.total_return * 100).toFixed(2) + '%' : '-' }}
                    </td>
                    <td class="py-2 px-3 text-right text-blue-400">
                      {{ stock.sharpe_ratio != null ? stock.sharpe_ratio.toFixed(2) : '-' }}
                    </td>
                    <td class="py-2 px-3 text-right text-purple-400">
                      {{ stock.win_rate != null ? (stock.win_rate * 100).toFixed(1) + '%' : '-' }}
                    </td>
                    <td class="py-2 px-3 text-right">{{ stock.total_trades ?? '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"></path>
              </svg>
              回测配置
            </h2>

            <div class="space-y-5">
              <div>
                <label class="block text-sm font-medium text-slate-300 mb-2 flex items-center justify-between">
                  <span>选择策略</span>
                  <button
                    @click="rescanStrategies"
                    class="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                  >
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    重新扫描
                  </button>
                </label>
                <div class="relative">
                  <div
                    class="min-h-[42px] bg-slate-700/50 border border-slate-600 rounded-lg p-2 cursor-pointer flex flex-wrap gap-2"
                    @click="showStrategyDropdown = !showStrategyDropdown"
                  >
                    <span v-if="store.selectedStrategies.length === 0" class="text-slate-400 py-1">点击选择策略...</span>
                    <span
                      v-for="s in store.selectedStrategies"
                      :key="s"
                      class="inline-flex items-center gap-1 px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-sm"
                    >
                      {{ s }}
                      <button @click.stop="removeStrategy(s)" class="hover:text-blue-200">×</button>
                    </span>
                  </div>
                  <div
                    v-if="showStrategyDropdown"
                    class="absolute z-10 w-full mt-1 bg-slate-700 border border-slate-600 rounded-lg shadow-xl max-h-60 overflow-y-auto"
                  >
                    <div class="p-2">
                      <input
                        v-model="stockInput"
                        type="text"
                        placeholder="搜索策略..."
                        class="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded text-sm mb-2"
                      />
                      <div
                        v-for="strategy in filteredStrategies"
                        :key="strategy.name"
                        class="px-3 py-2 hover:bg-slate-600 rounded cursor-pointer flex items-center gap-2"
                        @click="toggleStrategy(strategy.name)"
                      >
                        <input
                          type="checkbox"
                          :checked="store.selectedStrategies.includes(strategy.name)"
                          class="accent-blue-500"
                        />
                        <span class="text-sm">{{ strategy.name }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-300 mb-2">开始日期</label>
                  <input
                    v-model="store.startDate"
                    type="date"
                    class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-300 mb-2">结束日期</label>
                  <input
                    v-model="store.endDate"
                    type="date"
                    class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">股票选择</label>
                <div class="flex gap-2 mb-3">
                  <button
                    @click="setStockMode('all')"
                    :class="[
                      'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      store.stockSelectionMode === 'all'
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    ]"
                  >
                    全部
                  </button>
                  <button
                    @click="setStockMode('single')"
                    :class="[
                      'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      store.stockSelectionMode === 'single'
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    ]"
                  >
                    单只
                  </button>
                  <button
                    @click="setStockMode('multiple')"
                    :class="[
                      'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                      store.stockSelectionMode === 'multiple'
                        ? 'bg-blue-500 text-white'
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    ]"
                  >
                    多只
                  </button>
                </div>

                <div v-if="store.stockSelectionMode !== 'all'" class="flex gap-2 mb-2">
                  <input
                    v-model="stockInput"
                    type="text"
                    placeholder="输入股票代码"
                    class="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                    @keyup.enter="addStock"
                  />
                  <button
                    @click="addStock"
                    class="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-sm transition-colors"
                  >
                    添加
                  </button>
                </div>

                <div v-if="store.selectedStocks.length > 0" class="flex flex-wrap gap-2">
                  <span
                    v-for="stock in store.selectedStocks"
                    :key="stock"
                    class="inline-flex items-center gap-1 px-2 py-1 bg-purple-500/20 text-purple-400 rounded text-sm"
                  >
                    {{ stock }}
                    <button @click="removeStock(stock)" class="hover:text-purple-200">×</button>
                  </span>
                </div>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-300 mb-2">初始资金</label>
                <input
                  v-model.number="store.initialCapital"
                  type="number"
                  class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <!-- Parameter Sweep Input -->
              <div v-if="store.stockSelectionMode === 'all'">
                <label class="block text-sm font-medium text-slate-300 mb-2">参数扫描 (可选)</label>
                <input
                  v-model="paramGridInput"
                  type="text"
                  placeholder="如: threshold:6,8,10"
                  class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                />
                <p class="text-xs text-slate-500 mt-1">格式: threshold:6,8,10 (逗号分隔)</p>
              </div>

              <button
                @click="store.stockSelectionMode === 'all' ? store.submitBatchBacktest(paramGridInput) : store.runBacktest()"
                :disabled="store.isLoading || store.selectedStrategies.length === 0 || store.isBatchRunning"
                class="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:from-slate-600 disabled:to-slate-600 disabled:cursor-not-allowed rounded-lg font-medium transition-all flex items-center justify-center gap-2"
              >
                <svg v-if="store.isLoading || store.isBatchRunning" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {{ store.isBatchRunning ? '批量回测进行中...' : store.isLoading ? '运行中...' : '运行回测' }}
              </button>

              <div v-if="store.error" class="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                {{ store.error }}
              </div>
            </div>
          </div>

          <div v-if="store.hasResult && store.currentResult?.metrics" class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <h2 class="text-lg font-semibold mb-4">收益图表</h2>
            <div class="h-64">
              <Line :data="equityChartData" :options="equityChartOptions" />
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
              关键指标
            </h2>

            <div v-if="store.hasResult && store.currentResult?.metrics" class="space-y-4">
              <div class="grid grid-cols-2 gap-3">
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">总收益率</p>
                  <p :class="[
                    'text-xl font-bold',
                    store.currentResult.metrics.total_return >= 0 ? 'text-red-400' : 'text-green-400'
                  ]">
                    {{ (store.currentResult.metrics.total_return * 100).toFixed(2) }}%
                  </p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">年化收益率</p>
                  <p :class="[
                    'text-xl font-bold',
                    store.currentResult.metrics.annual_return >= 0 ? 'text-red-400' : 'text-green-400'
                  ]">
                    {{ (store.currentResult.metrics.annual_return * 100).toFixed(2) }}%
                  </p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">夏普比率</p>
                  <p class="text-xl font-bold text-blue-400">{{ store.currentResult.metrics.sharpe_ratio.toFixed(2) }}</p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">索提诺比率</p>
                  <p class="text-xl font-bold text-green-400">{{ store.currentResult.metrics.sortino_ratio.toFixed(2) }}</p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">卡尔马比率</p>
                  <p class="text-xl font-bold text-yellow-400">{{ store.currentResult.metrics.calmar_ratio.toFixed(2) }}</p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">最大回撤</p>
                  <p class="text-xl font-bold text-red-400">
                    {{ (store.currentResult.metrics.max_drawdown * 100).toFixed(2) }}%
                  </p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">胜率</p>
                  <p class="text-xl font-bold text-purple-400">
                    {{ (store.currentResult.metrics.win_rate * 100).toFixed(2) }}%
                  </p>
                </div>
                <div class="bg-slate-700/50 rounded-lg p-3">
                  <p class="text-slate-400 text-xs mb-1">交易次数</p>
                  <p class="text-xl font-bold text-slate-300">{{ store.currentResult.metrics.total_trades }}</p>
                </div>
              </div>
            </div>

            <div v-else-if="store.isLoading" class="flex items-center justify-center py-8">
              <svg class="w-8 h-8 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>

            <div v-else class="text-center py-8 text-slate-400">
              <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
              <p class="text-sm">配置参数并运行回测</p>
              <p class="text-xs mt-1">结果将显示在这里</p>
            </div>
          </div>

          <div v-if="store.hasResult && store.currentResult?.metrics" class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
            <h2 class="text-lg font-semibold mb-4">指标对比</h2>
            <div class="h-48">
              <Bar :data="metricsChartData" :options="metricsChartOptions" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 回测历史视图 -->
    <div v-if="currentView === 'history'" class="space-y-6">
      <!-- 筛选 -->
      <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
        <div class="flex flex-wrap gap-4 items-end">
          <div class="flex-1 min-w-[200px]">
            <label class="block text-sm text-slate-400 mb-1">策略名称</label>
            <input
              v-model="filterStrategyName"
              type="text"
              placeholder="输入策略名称"
              class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
              @keyup.enter="handleHistorySearch"
            />
          </div>
          <div class="flex-1 min-w-[150px]">
            <label class="block text-sm text-slate-400 mb-1">开始日期</label>
            <input
              v-model="filterStartDate"
              type="date"
              class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div class="flex-1 min-w-[150px]">
            <label class="block text-sm text-slate-400 mb-1">结束日期</label>
            <input
              v-model="filterEndDate"
              type="date"
              class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div class="flex gap-2">
            <button
              @click="handleHistorySearch"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
            >
              搜索
            </button>
            <button
              @click="handleHistoryReset"
              class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition-colors"
            >
              重置
            </button>
          </div>
        </div>
      </div>

      <!-- 表格 -->
      <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">回测记录</h2>
          <span class="text-sm text-slate-400">共 {{ historyTotal }} 条</span>
        </div>

        <!-- Loading -->
        <div v-if="isHistoryLoading" class="flex items-center justify-center py-12">
          <svg class="w-8 h-8 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0114 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>

        <!-- Empty -->
        <div v-else-if="historyRuns.length === 0" class="text-center py-12 text-slate-400">
          <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
          <p class="text-sm">暂无回测记录</p>
        </div>

        <!-- Table -->
        <div v-else class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="text-left text-slate-400 border-b border-slate-700">
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('run_id')">
                  回测ID {{ getHistorySortIcon('run_id') }}
                </th>
                <th class="pb-3 pr-4">
                  类型
                </th>
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('strategy_name')">
                  策略名称 {{ getHistorySortIcon('strategy_name') }}
                </th>
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('start_date')">
                  开始日期 {{ getHistorySortIcon('start_date') }}
                </th>
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('end_date')">
                  结束日期 {{ getHistorySortIcon('end_date') }}
                </th>
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('total_return')">
                  总股票数 {{ getHistorySortIcon('total_return') }}
                </th>
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('sharpe_ratio')">
                  成功数 {{ getHistorySortIcon('sharpe_ratio') }}
                </th>
                <th class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('max_drawdown')">
                  成功率 {{ getHistorySortIcon('max_drawdown') }}
                </th>
                <th class="pb-3 cursor-pointer hover:text-white transition-colors" @click="handleHistorySort('completed_at')">
                  运行时间 {{ getHistorySortIcon('completed_at') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="run in historyRuns"
                :key="run.run_id"
                class="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors"
                @click="viewHistoryDetail(run)"
              >
                <td class="py-3 pr-4 font-mono text-blue-400 text-sm">{{ run.run_id }}</td>
                <td class="py-3 pr-4">
                  <span
                    :class="[
                      'px-2 py-0.5 rounded text-xs font-medium',
                      run.type === 'batch' ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'
                    ]"
                  >
                    {{ run.type === 'batch' ? '批量' : '单次' }}
                  </span>
                </td>
                <td class="py-3 pr-4 text-slate-200">{{ run.strategy_name }}</td>
                <td class="py-3 pr-4 text-slate-300">{{ formatHistoryDate(run.start_date) }}</td>
                <td class="py-3 pr-4 text-slate-300">{{ formatHistoryDate(run.end_date) }}</td>
                <td class="py-3 pr-4">
                  <template v-if="run.type === 'batch'">
                    <span class="text-slate-200">{{ run.total_stocks ?? '-' }}</span>
                  </template>
                  <template v-else>
                    <span
                      :class="[
                        'font-medium',
                        (run.total_return ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'
                      ]"
                    >
                      {{ formatHistoryPercent(run.total_return) }}
                    </span>
                  </template>
                </td>
                <td class="py-3 pr-4">
                  <template v-if="run.type === 'batch'">
                    <span class="text-green-400">{{ run.success_count ?? '-' }}</span>
                  </template>
                  <template v-else>
                    <span class="text-blue-400">{{ formatHistoryNumber(run.sharpe_ratio) }}</span>
                  </template>
                </td>
                <td class="py-3 pr-4">
                  <template v-if="run.type === 'batch'">
                    <span
                      :class="[
                        'font-medium',
                        (run.success_rate ?? 0) >= 0.8 ? 'text-green-400' : (run.success_rate ?? 0) >= 0.5 ? 'text-yellow-400' : 'text-red-400'
                      ]"
                    >
                      {{ ((run.success_rate ?? 0) * 100).toFixed(1) }}%
                    </span>
                  </template>
                  <template v-else>
                    <span class="text-red-400">{{ formatHistoryPercent(run.max_drawdown) }}</span>
                  </template>
                </td>
                <td class="py-3 text-slate-400 text-sm">{{ formatHistoryDateTime(run.completed_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="historyRuns.length > 0" class="flex justify-between items-center mt-4 pt-4 border-t border-slate-700">
          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-400">每页</span>
            <select
              v-model="historyPageSize"
              class="px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm focus:outline-none focus:border-blue-500"
              @change="handleHistoryPageSizeChange(historyPageSize)"
            >
              <option v-for="size in historyPageSizeOptions" :key="size" :value="size">{{ size }}</option>
            </select>
            <span class="text-sm text-slate-400">条</span>
          </div>
          <div class="flex items-center gap-4">
            <button
              @click="handleHistoryPageChange(historyPage - 1)"
              :disabled="historyPage === 1"
              class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
            >
              上一页
            </button>
            <span class="text-slate-400 text-sm">第 {{ historyPage }} / {{ historyTotalPages }} 页</span>
            <button
              @click="handleHistoryPageChange(historyPage + 1)"
              :disabled="historyPage >= historyTotalPages"
              class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>