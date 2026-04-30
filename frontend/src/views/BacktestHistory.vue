<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

interface BacktestRun {
  run_id: string
  strategy_name: string
  start_date: string
  end_date: string
  initial_capital?: number
  status?: string
  completed_at?: string
  total_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
}

const router = useRouter()

const runs = ref<BacktestRun[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const pageSizeOptions = [10, 20, 50]

const filterStrategyName = ref('')
const filterStartDate = ref('')
const filterEndDate = ref('')

const sortColumn = ref<string>('completed_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

const isLoading = ref(false)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

async function fetchHistory() {
  isLoading.value = true
  try {
    const params: Record<string, any> = {
      page: currentPage.value,
      limit: pageSize.value
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
    runs.value = response.data.runs || []
    total.value = response.data.total || 0
  } catch (e) {
    console.error('Failed to fetch history:', e)
    runs.value = []
    total.value = 0
  } finally {
    isLoading.value = false
  }
}

function handleSearch() {
  currentPage.value = 1
  fetchHistory()
}

function handleReset() {
  filterStrategyName.value = ''
  filterStartDate.value = ''
  filterEndDate.value = ''
  currentPage.value = 1
  fetchHistory()
}

function handlePageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  fetchHistory()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchHistory()
}

function handleSort(column: string) {
  if (sortColumn.value === column) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = column
    sortOrder.value = 'desc'
  }
  fetchHistory()
}

function viewDetail(run: BacktestRun) {
  router.push({ name: 'backtest-detail', params: { runId: run.run_id } })
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  return dateStr
}

function formatNumber(num: number | undefined, decimals: number = 2): string {
  if (num === undefined || num === null) return '-'
  return num.toFixed(decimals)
}

function formatPercent(num: number | undefined): string {
  if (num === undefined || num === null) return '-'
  return (num * 100).toFixed(2) + '%'
}

function formatDateTime(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

function getSortIcon(column: string): string {
  if (sortColumn.value !== column) return ''
  return sortOrder.value === 'asc' ? '↑' : '↓'
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <header class="mb-8">
        <div class="flex items-center gap-4 mb-4">
          <router-link to="/" class="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
            <span>←</span>
            <span>返回回测</span>
          </router-link>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">回测历史</h1>
        <p class="text-slate-400 mt-1">查看历史回测记录</p>
      </header>

      <!-- Filter Section -->
      <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6 mb-6">
        <div class="flex flex-wrap gap-4 items-end">
          <!-- Strategy Name Filter -->
          <div class="flex-1 min-w-[200px]">
            <label class="block text-sm text-slate-400 mb-1">策略名称</label>
            <input
              v-model="filterStrategyName"
              type="text"
              placeholder="输入策略名称"
              class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
              @keyup.enter="handleSearch"
            />
          </div>

          <!-- Start Date Filter -->
          <div class="flex-1 min-w-[150px]">
            <label class="block text-sm text-slate-400 mb-1">开始日期</label>
            <input
              v-model="filterStartDate"
              type="date"
              class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <!-- End Date Filter -->
          <div class="flex-1 min-w-[150px]">
            <label class="block text-sm text-slate-400 mb-1">结束日期</label>
            <input
              v-model="filterEndDate"
              type="date"
              class="w-full px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-sm focus:outline-none focus:border-blue-500"
            />
          </div>

          <!-- Search Button -->
          <div class="flex gap-2">
            <button
              @click="handleSearch"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
            >
              搜索
            </button>
            <button
              @click="handleReset"
              class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition-colors"
            >
              重置
            </button>
          </div>
        </div>
      </div>

      <!-- Table Section -->
      <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
        <!-- Table Header -->
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-semibold">回测记录</h2>
          <span class="text-sm text-slate-400">共 {{ total }} 条</span>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="flex items-center justify-center py-12">
          <svg class="w-8 h-8 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>

        <!-- Empty State -->
        <div v-else-if="runs.length === 0" class="text-center py-12 text-slate-400">
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
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('run_id')"
                >
                  回测ID {{ getSortIcon('run_id') }}
                </th>
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('strategy_name')"
                >
                  策略名称 {{ getSortIcon('strategy_name') }}
                </th>
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('start_date')"
                >
                  开始日期 {{ getSortIcon('start_date') }}
                </th>
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('end_date')"
                >
                  结束日期 {{ getSortIcon('end_date') }}
                </th>
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('total_return')"
                >
                  总收益率 {{ getSortIcon('total_return') }}
                </th>
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('sharpe_ratio')"
                >
                  夏普比率 {{ getSortIcon('sharpe_ratio') }}
                </th>
                <th
                  class="pb-3 pr-4 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('max_drawdown')"
                >
                  最大回撤 {{ getSortIcon('max_drawdown') }}
                </th>
                <th
                  class="pb-3 cursor-pointer hover:text-white transition-colors"
                  @click="handleSort('completed_at')"
                >
                  运行时间 {{ getSortIcon('completed_at') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="run in runs"
                :key="run.run_id"
                class="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors"
                @click="viewDetail(run)"
              >
                <td class="py-3 pr-4 font-mono text-blue-400 text-sm">{{ run.run_id }}</td>
                <td class="py-3 pr-4 text-slate-200">{{ run.strategy_name }}</td>
                <td class="py-3 pr-4 text-slate-300">{{ formatDate(run.start_date) }}</td>
                <td class="py-3 pr-4 text-slate-300">{{ formatDate(run.end_date) }}</td>
                <td class="py-3 pr-4">
                  <span
                    :class="[
                      'font-medium',
                      (run.total_return ?? 0) >= 0 ? 'text-red-400' : 'text-green-400'
                    ]"
                  >
                    {{ formatPercent(run.total_return) }}
                  </span>
                </td>
                <td class="py-3 pr-4 text-blue-400">{{ formatNumber(run.sharpe_ratio) }}</td>
                <td class="py-3 pr-4 text-red-400">{{ formatPercent(run.max_drawdown) }}</td>
                <td class="py-3 text-slate-400 text-sm">{{ formatDateTime(run.completed_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="runs.length > 0" class="flex justify-between items-center mt-4 pt-4 border-t border-slate-700">
          <!-- Page Size Selector -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-400">每页</span>
            <select
              v-model="pageSize"
              class="px-2 py-1 bg-slate-700 border border-slate-600 rounded text-sm focus:outline-none focus:border-blue-500"
              @change="handlePageSizeChange(pageSize)"
            >
              <option v-for="size in pageSizeOptions" :key="size" :value="size">
                {{ size }}
              </option>
            </select>
            <span class="text-sm text-slate-400">条</span>
          </div>

          <!-- Page Info -->
          <div class="flex items-center gap-4">
            <button
              @click="handlePageChange(currentPage - 1)"
              :disabled="currentPage === 1"
              class="px-3 py-1 bg-slate-700 hover:bg-slate-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm transition-colors"
            >
              上一页
            </button>
            <span class="text-slate-400 text-sm">
              第 {{ currentPage }} / {{ totalPages }} 页
            </span>
            <button
              @click="handlePageChange(currentPage + 1)"
              :disabled="currentPage >= totalPages"
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