<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

interface Position {
  id: number
  code: string
  name: string
  strategy: string
  buy_date: string
  shares: number
  buy_price: number
  current_price: number
  profit_loss: number
  profit_pct: number
  stop_loss_pct: number
  notes: string
  position_amount: number
}

interface Summary {
  total_value: number
  total_cost: number
  holding_profit: number
  history_profit: number
  total_profit: number
  profit_pct: number
  count: number
  available_cash: number
}

const positions = ref<Position[]>([])
const summary = ref<Summary | null>(null)
const loading = ref(true)
const error = ref('')

const sortField = ref<string>('buy_date')
const sortDirection = ref<'asc' | 'desc'>('desc')

const handleSort = (field: string) => {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDirection.value = 'desc'
  }
}

const sortedPositions = computed(() => {
  const sorted = [...positions.value].sort((a, b) => {
    let aVal: any = a[sortField.value as keyof Position]
    let bVal: any = b[sortField.value as keyof Position]

    if (aVal === null || aVal === undefined) aVal = ''
    if (bVal === null || bVal === undefined) bVal = ''

    if (typeof aVal === 'string' && typeof bVal === 'string') {
      return sortDirection.value === 'asc' 
        ? aVal.localeCompare(bVal) 
        : bVal.localeCompare(aVal)
    }

    return sortDirection.value === 'asc' 
      ? (aVal > bVal ? 1 : -1) 
      : (aVal < bVal ? 1 : -1)
  })
  return sorted
})

const fetchPositions = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/positions')
    positions.value = response.data.positions || []
    summary.value = response.data.summary || null
  } catch (e) {
    error.value = '获取持仓数据失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchPositions()
})

const formatMoney = (value: number | undefined | null) => {
  if (value === null || value === undefined) return '--'
  const absValue = Math.abs(value)
  if (absValue >= 10000) {
    return (value >= 0 ? '+' : '') + (value / 10000).toFixed(2) + '万'
  }
  return (value >= 0 ? '+' : '') + value.toFixed(2)
}

const formatPercent = (value: number | undefined | null) => {
  if (value === null || value === undefined) return '--'
  return (value >= 0 ? '+' : '') + value.toFixed(2) + '%'
}

const getProfitClass = (val: number | undefined | null) => {
  if (val === null || val === undefined || val === 0) return 'profit-neutral'
  return val > 0 ? 'profit-positive' : 'profit-negative'
}

defineProps<{
  embedded?: boolean
}>()
</script>

<template>
  <div :class="embedded ? '' : 'max-w-7xl mx-auto'">
    <!-- Positions Table -->
    <div class="glass-card p-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
          </svg>
          当前持仓
        </h2>
        <div class="flex gap-4">
          <div class="text-center">
            <p class="text-slate-400 text-xs">持仓盈亏</p>
            <p class="text-xl font-bold" :class="summary ? getProfitClass(summary.holding_profit) : ''">
              {{ summary ? formatMoney(summary.holding_profit) : '--' }}
            </p>
          </div>
          <div class="text-center">
            <p class="text-slate-400 text-xs">持仓数量</p>
            <p class="text-xl font-bold">{{ summary?.count || 0 }} 只</p>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <svg class="w-8 h-8 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-12 text-red-400">
        {{ error }}
      </div>

      <!-- Empty State -->
      <div v-else-if="positions.length === 0" class="text-center py-12 text-slate-400">
        暂无持仓
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="text-slate-400 text-sm border-b border-slate-700">
              <th 
                class="text-left py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('name')"
              >
                股票
                <span v-if="sortField === 'name'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('buy_price')"
              >
                买入价
                <span v-if="sortField === 'buy_price'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('current_price')"
              >
                现价
                <span v-if="sortField === 'current_price'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('shares')"
              >
                数量
                <span v-if="sortField === 'shares'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('position_amount')"
              >
                持仓金额
                <span v-if="sortField === 'position_amount'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('profit_loss')"
              >
                盈亏
                <span v-if="sortField === 'profit_loss'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('profit_pct')"
              >
                盈亏%
                <span v-if="sortField === 'profit_pct'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-right py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('stop_loss_pct')"
              >
                止损%
                <span v-if="sortField === 'stop_loss_pct'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th 
                class="text-left py-3 px-2 cursor-pointer hover:text-blue-400 transition-colors"
                @click="handleSort('buy_date')"
              >
                买入日期
                <span v-if="sortField === 'buy_date'" class="ml-1">
                  {{ sortDirection === 'asc' ? '▲' : '▼' }}
                </span>
              </th>
              <th class="text-left py-3 px-2 w-40">买入原因</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="pos in sortedPositions"
              :key="pos.id"
              class="table-row border-b border-slate-800"
            >
              <td class="py-3 px-2">
                <div class="flex items-center gap-2">
                  <span class="font-medium">{{ pos.name }}</span>
                  <span class="text-slate-500 text-sm">{{ pos.code }}</span>
                </div>
                <span class="text-xs text-slate-500">{{ pos.strategy || '' }}</span>
              </td>
              <td class="text-right py-3 px-2">{{ pos.buy_price ? pos.buy_price.toFixed(2) : '--' }}</td>
              <td class="text-right py-3 px-2">{{ pos.current_price ? pos.current_price.toFixed(2) : '--' }}</td>
              <td class="text-right py-3 px-2">{{ pos.shares || 0 }}</td>
              <td class="text-right py-3 px-2 text-blue-400">{{ formatMoney(pos.position_amount) }}</td>
              <td class="text-right py-3 px-2" :class="getProfitClass(pos.profit_loss)">{{ formatMoney(pos.profit_loss) }}</td>
              <td class="text-right py-3 px-2" :class="getProfitClass(pos.profit_pct)">{{ formatPercent(pos.profit_pct) }}</td>
              <td class="text-right py-3 px-2 text-slate-400">{{ ((pos.stop_loss_pct || 0) * 100).toFixed(0) }}%</td>
              <td class="text-left py-3 px-2 text-slate-400">{{ pos.buy_date || '--' }}</td>
              <td class="text-left py-3 px-2 text-slate-400 whitespace-normal w-40">{{ pos.notes || '--' }}</td>
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

.profit-neutral {
  color: #94a3b8;
}

.table-row:hover {
  background: rgba(59, 130, 246, 0.1);
}
</style>
