<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  runId: string
  disabled?: boolean
}>()

const isOpen = ref(false)
const isExporting = ref(false)

const exportData = async (format: 'csv' | 'json') => {
  isOpen.value = false
  isExporting.value = true

  try {
    const response = await fetch(`/api/backtest/${props.runId}/export?format=${format}`)
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || '导出失败')
    }

    const blob = await response.blob()
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `backtest_${props.runId}_${new Date().toISOString().split('T')[0]}.${format}`
    
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (match && match[1]) {
        filename = match[1].replace(/['"]/g, '')
      }
    }

    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Export failed:', error)
    alert(error instanceof Error ? error.message : '导出失败')
  } finally {
    isExporting.value = false
  }
}

const toggleDropdown = () => {
  if (!props.disabled && !isExporting.value) {
    isOpen.value = !isOpen.value
  }
}

const closeDropdown = () => {
  isOpen.value = false
}
</script>

<template>
  <div class="relative">
    <button
      type="button"
      :disabled="disabled || isExporting"
      @click="toggleDropdown"
      class="px-4 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 
             text-slate-200 text-sm rounded-lg border border-slate-600 transition-colors
             flex items-center gap-2"
    >
      <svg
        v-if="isExporting"
        class="w-4 h-4 animate-spin"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      <svg
        v-else
        class="w-4 h-4"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      <span>{{ isExporting ? '导出中...' : '导出' }}</span>
      <svg
        class="w-4 h-4 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="isOpen"
        class="absolute right-0 mt-2 w-40 bg-slate-800 border border-slate-600 rounded-lg shadow-xl overflow-hidden z-50"
      >
        <button
          type="button"
          @click="exportData('csv')"
          class="w-full px-4 py-2.5 text-left text-slate-200 hover:bg-slate-700 transition-colors flex items-center gap-2"
        >
          <svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>CSV (交易记录)</span>
        </button>
        <button
          type="button"
          @click="exportData('json')"
          class="w-full px-4 py-2.5 text-left text-slate-200 hover:bg-slate-700 transition-colors flex items-center gap-2 border-t border-slate-700"
        >
          <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
          <span>JSON (完整数据)</span>
        </button>
      </div>
    </Transition>

    <div
      v-if="isOpen"
      class="fixed inset-0 z-40"
      @click="closeDropdown"
    ></div>
  </div>
</template>
