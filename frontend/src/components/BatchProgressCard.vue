<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  taskId?: string
  status: 'idle' | 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  message?: string
  errorMessage?: string | null
  startedAt?: string | null
  completedAt?: string | null
}>()

const borderClass = computed(() => {
  switch (props.status) {
    case 'pending': return 'border-blue-500/50'
    case 'running': return 'border-blue-500/50'
    case 'completed': return 'border-green-500/50'
    case 'failed': return 'border-red-500/50'
    default: return 'border-slate-600'
  }
})

const textClass = computed(() => {
  switch (props.status) {
    case 'pending': return 'text-blue-400'
    case 'running': return 'text-blue-400'
    case 'completed': return 'text-green-400'
    case 'failed': return 'text-red-400'
    default: return 'text-slate-300'
  }
})

const statusText = computed(() => {
  switch (props.status) {
    case 'pending': return '等待开始'
    case 'running': return '进行中'
    case 'completed': return '已完成'
    case 'failed': return '失败'
    default: return ''
  }
})

function formatTime(iso: string | null | undefined): string {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('zh-CN')
}
</script>

<template>
  <div v-if="status !== 'idle'" class="bg-slate-800/80 border rounded-xl p-4 mb-4" :class="borderClass">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-3">
        <!-- Spinner for pending -->
        <svg v-if="status === 'pending'" class="w-5 h-5 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <!-- Check for completed -->
        <svg v-if="status === 'completed'" class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
        </svg>
        <!-- X for failed -->
        <svg v-if="status === 'failed'" class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
        <!-- Spinner for running -->
        <svg v-if="status === 'running'" class="w-5 h-5 animate-spin text-blue-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span class="font-medium" :class="textClass">{{ statusText }}</span>
      </div>
      <span v-if="status === 'running'" class="text-sm text-blue-400">{{ progress }}%</span>
    </div>

    <!-- Progress bar for running -->
    <div v-if="status === 'running'" class="w-full bg-slate-700 rounded-full h-2 mb-2">
      <div class="bg-blue-500 h-2 rounded-full transition-all" :style="{ width: progress + '%' }"></div>
    </div>

    <!-- Message -->
    <p v-if="message && status !== 'completed'" class="text-slate-400 text-sm">{{ message }}</p>

    <!-- Error message -->
    <p v-if="status === 'failed' && errorMessage" class="text-red-400 text-sm mt-1">{{ errorMessage }}</p>

    <!-- Timestamps -->
    <div v-if="startedAt || completedAt" class="text-xs text-slate-500 mt-2 flex justify-between">
      <span v-if="startedAt">开始: {{ formatTime(startedAt) }}</span>
      <span v-if="completedAt">完成: {{ formatTime(completedAt) }}</span>
    </div>
  </div>
</template>
