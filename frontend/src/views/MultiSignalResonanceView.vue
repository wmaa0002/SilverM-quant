<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface StockSignal {
  code: string
  name: string
  signal_count: number
  signals: string[]
  close: number
  change_pct: number
}

interface ResonanceData {
  date: string
  count: number
  stocks: StockSignal[]
}

interface TrendData {
  dates: string[]
  signal_data: Record<string, number[]>
  total_counts: number[]
}

const loading = ref(true)
const selectedDate = ref('')
const dateOptions = ref<{ value: string; label: string }[]>([])
const resonanceData = ref<ResonanceData | null>(null)
const error = ref('')
const trendData = ref<TrendData | null>(null)
const trendLoading = ref(false)

const SIGNAL_COLORS: Record<string, string> = {
  B1: '#60a5fa',
  B2: '#34d399',
  BLK: '#fb923c',
  DL: '#a78bfa',
  DZ30: '#22d3ee',
  SCB: '#f472b6',
  BLKB2: '#a3e635',
}

const chartData = computed(() => {
  if (!trendData.value) return { labels: [], datasets: [] }

  const { dates, signal_data, total_counts } = trendData.value

  const signalDatasets = Object.entries(signal_data || {}).map(([signal, data]) => ({
    label: signal,
    data,
    borderColor: SIGNAL_COLORS[signal] || '#94a3b8',
    backgroundColor: (SIGNAL_COLORS[signal] || '#94a3b8') + '22',
    borderWidth: 1.5,
    pointRadius: 2,
    tension: 0.3,
    yAxisID: 'y1',
    fill: false,
  }))

  return {
    labels: dates || [],
    datasets: [
      {
        label: '总共振数',
        data: total_counts || [],
        borderColor: '#f8fafc',
        backgroundColor: 'rgba(248,250,252,0.08)',
        borderWidth: 2.5,
        pointRadius: 2,
        tension: 0.3,
        yAxisID: 'y',
        fill: true,
      },
      ...signalDatasets,
    ],
  }
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      position: 'top' as const,
      labels: {
        color: '#94a3b8',
        font: { size: 11 },
        usePointStyle: true,
        pointStyleWidth: 10,
      },
    },
    title: {
      display: false,
    },
    tooltip: {
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: 'rgba(51,65,85,0.7)',
      borderWidth: 1,
      titleColor: '#f1f5f9',
      bodyColor: '#94a3b8',
    },
  },
  scales: {
    x: {
      ticks: {
        color: '#64748b',
        font: { size: 10 },
        maxTicksLimit: 15,
        maxRotation: 45,
      },
      grid: { color: 'rgba(51,65,85,0.3)' },
    },
    y: {
      type: 'linear' as const,
      position: 'left' as const,
      title: { display: true, text: '总共振数', color: '#f1f5f9', font: { size: 11 } },
      ticks: { color: '#f1f5f9', font: { size: 10 } },
      grid: { color: 'rgba(51,65,85,0.3)' },
    },
    y1: {
      type: 'linear' as const,
      position: 'right' as const,
      title: { display: true, text: '各信号数', color: '#94a3b8', font: { size: 11 } },
      ticks: { color: '#94a3b8', font: { size: 10 } },
      grid: { drawOnChartArea: false },
    },
  },
}))

const fetchData = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await axios.get(`/api/multi-signal-resonance?date=${selectedDate.value}`)
    resonanceData.value = response.data
  } catch (e) {
    error.value = '加载失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

const fetchTrendData = async () => {
  try {
    trendLoading.value = true
    const response = await axios.get('/api/multi-signal-trend')
    trendData.value = response.data
  } catch (e) {
    console.error('Failed to fetch trend data:', e)
  } finally {
    trendLoading.value = false
  }
}

const fetchDates = async () => {
  try {
    const response = await axios.get('/api/multi-signal-resonance/dates')
    dateOptions.value = response.data.dates || []
    if (dateOptions.value.length > 0) {
      selectedDate.value = dateOptions.value[0].value
    }
  } catch (e) {
    console.error('Failed to fetch dates:', e)
  }
}

const totalSignals = () => {
  if (!resonanceData.value?.stocks) return 0
  return resonanceData.value.stocks.reduce((sum, st) => sum + st.signal_count, 0)
}

const getChangeClass = (changePct: number) => {
  if (changePct > 0) return 'change-up'
  if (changePct < 0) return 'change-down'
  return 'change-zero'
}

const onDateChange = async () => {
  await fetchData()
}

onMounted(async () => {
  await fetchDates()
  await Promise.all([fetchData(), fetchTrendData()])
})
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <!-- Filter -->
    <div class="glass-card p-4 mb-6 flex items-center gap-4">
      <label class="text-slate-400 font-medium">选择日期:</label>
      <select
        v-model="selectedDate"
        @change="onDateChange"
        class="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
      >
        <option v-for="opt in dateOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="glass-card p-4 text-center">
        <p class="text-3xl font-bold text-blue-400">{{ resonanceData?.count || '-' }}</p>
        <p class="text-sm text-slate-400 mt-1">共振股票数</p>
      </div>
      <div class="glass-card p-4 text-center">
        <p class="text-3xl font-bold text-emerald-400">{{ totalSignals() || '-' }}</p>
        <p class="text-sm text-slate-400 mt-1">总信号数</p>
      </div>
      <div class="glass-card p-4 text-center">
        <p class="text-3xl font-bold text-purple-400">{{ resonanceData?.date || '-' }}</p>
        <p class="text-sm text-slate-400 mt-1">当前日期</p>
      </div>
    </div>

    <!-- Trend Chart -->
    <div class="glass-card p-4 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-slate-200 font-semibold text-base">信号趋势图</h2>
        <span v-if="trendLoading" class="text-slate-400 text-sm">加载中...</span>
      </div>
      <div v-if="trendData && !trendLoading" class="chart-container">
        <Line :data="chartData" :options="chartOptions" />
      </div>
      <div v-else-if="trendLoading" class="chart-container flex items-center justify-center">
        <p class="text-slate-400 text-sm">趋势数据加载中...</p>
      </div>
      <div v-else class="chart-container flex items-center justify-center">
        <p class="text-slate-500 text-sm">暂无趋势数据</p>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="glass-card p-12 text-center">
      <p class="text-slate-400">加载中...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="glass-card p-12 text-center text-red-400">
      {{ error }}
    </div>

    <!-- Table -->
    <div v-else class="glass-card overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-slate-700">
            <th class="text-left py-3 px-4 text-slate-400 font-medium text-sm">代码</th>
            <th class="text-left py-3 px-4 text-slate-400 font-medium text-sm">名称</th>
            <th class="text-center py-3 px-4 text-slate-400 font-medium text-sm">信号数</th>
            <th class="text-left py-3 px-4 text-slate-400 font-medium text-sm">信号列表</th>
            <th class="text-right py-3 px-4 text-slate-400 font-medium text-sm">收盘价</th>
            <th class="text-right py-3 px-4 text-slate-400 font-medium text-sm">涨跌幅</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!resonanceData?.stocks?.length">
            <td colspan="6" class="text-center py-8 text-slate-400">暂无数据</td>
          </tr>
          <tr
            v-for="stock in resonanceData?.stocks"
            :key="stock.code"
            class="table-row border-b border-slate-800"
          >
            <td class="py-3 px-4 stock-code">{{ stock.code }}</td>
            <td class="py-3 px-4 stock-name">{{ stock.name }}</td>
            <td class="py-3 px-4 text-center"><strong>{{ stock.signal_count }}</strong></td>
            <td class="py-3 px-4">
              <div class="flex gap-1 flex-wrap">
                <span
                  v-for="signal in stock.signals"
                  :key="signal"
                  :class="'signal-tag ' + signal"
                >
                  {{ signal }}
                </span>
              </div>
            </td>
            <td class="py-3 px-4 text-right">{{ stock.close.toFixed(2) }}</td>
            <td class="py-3 px-4 text-right" :class="getChangeClass(stock.change_pct)">
              {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.glass-card {
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(51, 65, 85, 0.5);
  border-radius: 12px;
}

.chart-container {
  height: 320px;
  position: relative;
}

.signal-tag {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.signal-tag.B1 { background: rgba(59, 130, 246, 0.3); color: #60a5fa; }
.signal-tag.B2 { background: rgba(16, 185, 129, 0.3); color: #34d399; }
.signal-tag.BLK { background: rgba(249, 115, 22, 0.3); color: #fb923c; }
.signal-tag.DL { background: rgba(139, 92, 246, 0.3); color: #a78bfa; }
.signal-tag.DZ30 { background: rgba(6, 182, 212, 0.3); color: #22d3ee; }
.signal-tag.SCB { background: rgba(236, 72, 153, 0.3); color: #f472b6; }
.signal-tag.BLKB2 { background: rgba(132, 204, 22, 0.3); color: #a3e635; }

.stock-code { font-weight: 600; color: #f1f5f9; }
.stock-name { color: #94a3b8; }

.change-up { color: #ef4444; }
.change-down { color: #10b981; }
.change-zero { color: #94a3b8; }

.table-row:hover { background: rgba(59, 130, 246, 0.1); }
</style>
