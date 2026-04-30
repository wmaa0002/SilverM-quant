<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface Strategy {
  name: string
  description?: string
  threshold_required?: boolean
  min_data_days?: number
}

const strategies = ref<Strategy[]>([])
const isLoading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

async function fetchStrategies() {
  isLoading.value = true
  try {
    const response = await axios.get('/api/backtest/strategies')
    strategies.value = (response.data.strategies || []).map((name: string) => ({ name }))
    message.value = ''
  } catch (e) {
    showMessage('获取策略列表失败', 'error')
  } finally {
    isLoading.value = false
  }
}

async function registerStrategies() {
  isLoading.value = true
  try {
    const response = await axios.post('/api/backtest/register-strategies')
    strategies.value = (response.data.strategies || []).map((name: string) => ({ name }))
    showMessage(`注册成功：${response.data.loaded} 个策略`, 'success')
  } catch (e: any) {
    showMessage('注册策略失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    isLoading.value = false
  }
}

async function deleteStrategy(name: string) {
  if (!confirm(`确定删除策略 "${name}" 吗？`)) return

  isLoading.value = true
  try {
    await axios.delete(`/api/backtest/strategies/${encodeURIComponent(name)}`)
    await fetchStrategies()
    showMessage(`删除策略 "${name}" 成功`, 'success')
  } catch (e: any) {
    showMessage('删除策略失败: ' + (e.response?.data?.error || e.message), 'error')
  } finally {
    isLoading.value = false
  }
}

function showMessage(msg: string, type: 'success' | 'error') {
  message.value = msg
  messageType.value = type
  setTimeout(() => { message.value = '' }, 5000)
}

onMounted(() => {
  fetchStrategies()
})
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
    <div class="max-w-5xl mx-auto">
      <header class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold tracking-tight">策略管理</h1>
            <p class="text-slate-400 mt-1">查看、注册和删除策略</p>
          </div>
          <button
            @click="registerStrategies"
            :disabled="isLoading"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
            </svg>
            注册策略
          </button>
        </div>
      </header>

      <div v-if="message" :class="[
        'mb-6 p-4 rounded-lg text-sm',
        messageType === 'success' ? 'bg-green-500/20 border border-green-500/50 text-green-400' : 'bg-red-500/20 border border-red-500/50 text-red-400'
      ]">
        {{ message }}
      </div>

      <div class="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
        <div v-if="isLoading && strategies.length === 0" class="flex items-center justify-center py-12">
          <svg class="w-8 h-8 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 0114 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>

        <div v-else-if="strategies.length === 0" class="text-center py-12">
          <svg class="w-16 h-16 mx-auto mb-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
          </svg>
          <p class="text-slate-400 mb-4">暂无已注册的策略</p>
          <button
            @click="registerStrategies"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors"
          >
            点击注册策略
          </button>
        </div>

        <div v-else>
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold">策略列表 ({{ strategies.length }})</h2>
            <button
              @click="fetchStrategies"
              :disabled="isLoading"
              class="text-sm text-blue-400 hover:text-blue-300 disabled:text-slate-500"
            >
              刷新
            </button>
          </div>

          <table class="w-full">
            <thead>
              <tr class="text-left text-slate-400 border-b border-slate-700">
                <th class="pb-3 pr-4">策略名称</th>
                <th class="pb-3 pr-4">需要threshold</th>
                <th class="pb-3 pr-4">最小数据天数</th>
                <th class="pb-3">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="strategy in strategies"
                :key="strategy.name"
                class="border-b border-slate-700/50 hover:bg-slate-700/30"
              >
                <td class="py-4 pr-4 font-medium">{{ strategy.name }}</td>
                <td class="py-4 pr-4">
                  <span v-if="strategy.threshold_required" class="text-green-400">是</span>
                  <span v-else class="text-slate-500">否</span>
                </td>
                <td class="py-4 pr-4">{{ strategy.min_data_days || '-' }}</td>
                <td class="py-4">
                  <button
                    @click="deleteStrategy(strategy.name)"
                    class="text-red-400 hover:text-red-300 text-sm"
                  >
                    删除
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>