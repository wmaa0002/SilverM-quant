<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const signals = ref<any>(null)
const loading = ref(true)

const fetchSignals = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/signals')
    signals.value = response.data
  } catch (e) {
    console.error('Failed to fetch signals:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchSignals()
})

const activeTab = ref<'buy' | 'sell'>('buy')

const buySignals = computed(() =>
  (signals.value?.signals || []).filter((s: any) => s.buy_signals?.length > 0)
)
const sellSignals = computed(() =>
  (signals.value?.signals || []).filter((s: any) => s.sell_signals?.length > 0)
)

const displayedSignals = computed(() =>
  activeTab.value === 'buy' ? buySignals.value : sellSignals.value
)

const getSignalList = (signal: any) =>
  activeTab.value === 'buy' ? signal.buy_signals : signal.sell_signals
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <!-- Signals Content -->
    <div class="glass-card p-5">
      <!-- Header -->
      <div class="flex items-center justify-between mb-5">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
            <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
          </div>
          <div>
            <h3 class="text-lg font-semibold text-slate-100">交易信号</h3>
            <p class="text-xs text-slate-400">点击查看详情</p>
          </div>
        </div>
      </div>
      
      <!-- Tab Buttons -->
      <div class="flex gap-2 mb-4">
        <button 
          @click="activeTab = 'buy'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeTab === 'buy' ? 'bg-red-900/50 text-red-400 border border-red-700' : 'bg-slate-800/50 text-slate-400 border border-slate-700 hover:bg-slate-700/50'"
        >
          买入信号 ({{ buySignals.length }})
        </button>
        <button 
          @click="activeTab = 'sell'"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="activeTab === 'sell' ? 'bg-green-900/50 text-green-400 border border-green-700' : 'bg-slate-800/50 text-slate-400 border border-slate-700 hover:bg-slate-700/50'"
        >
          卖出信号 ({{ sellSignals.length }})
        </button>
      </div>
      
      <!-- Signal Cards -->
      <div v-if="loading" class="text-center py-8 text-slate-400">
        加载中...
      </div>
      <div v-else-if="displayedSignals.length === 0" class="text-center py-8 text-slate-400">
        暂无信号
      </div>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div
          v-for="signal in displayedSignals"
          :key="signal.code"
          class="p-4 rounded-xl border transition-all duration-200"
          :class="activeTab === 'buy' ? 'bg-gradient-to-r from-red-500/10 to-transparent border-red-500/20 hover:border-red-500/40' : 'bg-gradient-to-r from-green-500/10 to-transparent border-green-500/20 hover:border-green-500/40'"
        >
          <div class="flex items-start justify-between mb-2">
            <div>
              <span class="text-slate-100 font-medium">{{ signal.name }}</span>
              <span class="text-slate-500 text-sm ml-2">{{ signal.code }}</span>
            </div>
            <span class="text-slate-100 font-semibold">¥{{ (signal.close || 0).toFixed(2) }}</span>
          </div>
          <div class="flex flex-wrap gap-2 mt-2">
            <span
              v-for="sig in getSignalList(signal)"
              :key="sig.strategy"
              class="px-2 py-0.5 rounded text-xs font-medium"
              :class="activeTab === 'buy' ? 'bg-red-500/20 text-red-300' : 'bg-green-500/20 text-green-300'"
            >
              {{ sig.strategy }} {{ sig.score.toFixed(1) }}分
            </span>
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
</style>