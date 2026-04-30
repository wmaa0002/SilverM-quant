<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

interface Signal {
  code: string
  name: string
  close: number
  change_pct: number
  buy_signals: Array<{strategy: string, score: number}>
  sell_signals: Array<{strategy: string, score: number}>
}

const signals = ref<Signal[]>([])
const loading = ref(true)
const error = ref('')
const currentSignalType = ref<'buy' | 'sell'>('buy')

const fetchSignals = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/signals')
    signals.value = response.data.signals || []
  } catch (e) {
    error.value = '获取信号数据失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSignals()
})

const filteredSignals = computed(() => {
  return signals.value.filter(s => {
    if (currentSignalType.value === 'buy') {
      return s.buy_signals?.length > 0
    } else {
      return s.sell_signals?.length > 0
    }
  })
})

const formatPercent = (value: number | undefined | null) => {
  if (value === null || value === undefined) return '--'
  return (value >= 0 ? '+' : '') + value.toFixed(2) + '%'
}

const getSignalList = (signal: Signal) =>
  currentSignalType.value === 'buy' ? signal.buy_signals : signal.sell_signals
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <!-- Signal Tabs -->
    <div class="glass-card p-4 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
          </svg>
          交易信号
          <span class="ml-2 text-sm text-slate-400">(共 {{ filteredSignals.length }} 条)</span>
        </h2>
        <div class="flex gap-2">
          <button
            @click="currentSignalType = 'buy'"
            :class="currentSignalType === 'buy' ? 'bg-red-500 hover:bg-red-600' : 'bg-slate-700 hover:bg-slate-600'"
            class="flex-1 py-2 px-4 rounded-lg text-white font-medium transition-colors"
          >
            买入信号
          </button>
          <button
            @click="currentSignalType = 'sell'"
            :class="currentSignalType === 'sell' ? 'bg-green-500 hover:bg-green-600' : 'bg-slate-700 hover:bg-slate-600'"
            class="flex-1 py-2 px-4 rounded-lg text-white font-medium transition-colors"
          >
            卖出信号
          </button>
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
      <div v-else-if="filteredSignals.length === 0" class="text-center py-12 text-slate-400">
        暂无信号
      </div>

      <!-- Signal Cards -->
      <div v-else class="space-y-3 max-h-[500px] overflow-y-auto">
        <div
          v-for="signal in filteredSignals"
          :key="signal.code"
          class="p-3 rounded-lg border"
          :class="currentSignalType === 'buy' ? 'signal-buy border-red-200' : 'signal-sell border-green-200'"
        >
          <div class="flex justify-between items-start">
            <div>
              <div class="font-medium text-black">{{ signal.name }}</div>
              <div class="text-sm text-gray-600">{{ signal.code }}</div>
            </div>
            <div class="text-right">
              <div class="flex flex-wrap gap-1 justify-end">
                <span
                  v-for="sig in getSignalList(signal)"
                  :key="sig.strategy"
                  class="px-2 py-0.5 rounded text-xs font-medium"
                  :class="currentSignalType === 'buy' ? 'bg-red-500/30 text-red-700' : 'bg-green-500/30 text-green-700'"
                >
                  {{ sig.strategy }} {{ sig.score.toFixed(1) }}分
                </span>
              </div>
              <div class="text-xs mt-1" :class="currentSignalType === 'buy' ? 'text-red-600' : 'text-green-600'">
                {{ currentSignalType === 'buy' ? '买入' : '卖出' }}
              </div>
            </div>
          </div>
          <div class="mt-2 flex justify-between text-sm text-gray-600">
            <span>现价: {{ signal.close?.toFixed(2) || '--' }}</span>
            <span>涨跌: <span :class="signal.change_pct >= 0 ? 'text-red-700' : 'text-green-700'">{{ formatPercent(signal.change_pct) }}</span></span>
          </div>
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

.signal-buy {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
}

.signal-sell {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
}
</style>
