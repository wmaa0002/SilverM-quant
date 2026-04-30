<script setup lang="ts">
import { ref, computed } from 'vue'

export interface Strategy {
  id: string
  name: string
  description?: string
  defaultThreshold?: number
}

const props = defineProps<{
  modelValue: string[]
  availableStrategies: Strategy[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const isOpen = ref(false)
const strategyParams = ref<Record<string, number>>({})

// Initialize params when strategies change
const initializeParams = () => {
  props.availableStrategies.forEach((s) => {
    if (strategyParams.value[s.id] === undefined) {
      strategyParams.value[s.id] = s.defaultThreshold ?? 0
    }
  })
}

// Watch for availableStrategies changes
computed(() => {
  initializeParams()
  return props.availableStrategies
})

const selectedStrategies = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isNoneSelected = computed(() => {
  return selectedStrategies.value.length === 0
})

const toggleStrategy = (strategyId: string) => {
  const newValue = selectedStrategies.value.includes(strategyId)
    ? selectedStrategies.value.filter((id) => id !== strategyId)
    : [...selectedStrategies.value, strategyId]
  selectedStrategies.value = newValue
}

const selectAll = () => {
  selectedStrategies.value = props.availableStrategies.map((s) => s.id)
}

const deselectAll = () => {
  selectedStrategies.value = []
}

const toggleDropdown = () => {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    initializeParams()
  }
}

const closeDropdown = () => {
  isOpen.value = false
}

const getStrategyById = (id: string): Strategy | undefined => {
  return props.availableStrategies.find((s) => s.id === id)
}

const updateThreshold = (strategyId: string, value: number) => {
  strategyParams.value[strategyId] = value
}

// Expose params for parent to retrieve
defineExpose({
  getStrategyParams: () => ({ ...strategyParams.value })
})
</script>

<template>
  <div class="relative">
    <!-- Dropdown Trigger -->
    <button
      type="button"
      @click="toggleDropdown"
      class="w-full px-4 py-2.5 text-left bg-slate-800 border border-slate-600 rounded-lg 
             hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 
             transition-all duration-200 flex items-center justify-between gap-2"
    >
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <span v-if="isNoneSelected" class="text-slate-400">选择策略...</span>
        <span v-else class="text-slate-200">
          已选择 {{ selectedStrategies.length }} 个策略
        </span>
      </div>
      <svg
        class="w-5 h-5 text-slate-400 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Selected Tags Display -->
    <div v-if="selectedStrategies.length > 0" class="mt-2 flex flex-wrap gap-2">
      <div
        v-for="strategyId in selectedStrategies"
        :key="strategyId"
        class="group flex items-center gap-1.5 px-2.5 py-1 bg-blue-500/20 border border-blue-500/30 
               rounded-full text-blue-400 text-sm"
      >
        <span>{{ getStrategyById(strategyId)?.name || strategyId }}</span>
        <button
          type="button"
          @click.stop="toggleStrategy(strategyId)"
          class="w-4 h-4 rounded-full hover:bg-blue-500/30 flex items-center justify-center 
                 transition-colors"
        >
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Dropdown Panel -->
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
        class="absolute z-50 mt-2 w-full bg-slate-800 border border-slate-600 rounded-lg shadow-xl 
               overflow-hidden"
      >
        <!-- Header with Select All/None -->
        <div class="flex items-center justify-between px-3 py-2 border-b border-slate-700 bg-slate-800/80">
          <button
            type="button"
            @click="selectAll"
            class="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            全选
          </button>
          <button
            type="button"
            @click="deselectAll"
            class="text-sm text-slate-400 hover:text-slate-300 transition-colors"
          >
            清空
          </button>
        </div>

        <!-- Strategy List -->
        <div class="max-h-64 overflow-y-auto custom-scrollbar">
          <div
            v-for="strategy in availableStrategies"
            :key="strategy.id"
            class="px-3 py-2.5 hover:bg-slate-700/50 transition-colors border-b border-slate-700/50 last:border-0"
          >
            <!-- Checkbox and Name -->
            <label class="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                :checked="selectedStrategies.includes(strategy.id)"
                @change="toggleStrategy(strategy.id)"
                class="mt-1 w-4 h-4 rounded border-slate-500 bg-slate-700 text-blue-500 
                       focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-0 cursor-pointer"
              />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-slate-200">{{ strategy.name }}</span>
                  <!-- Description Tooltip -->
                  <div class="relative group">
                    <svg
                      class="w-4 h-4 text-slate-500 hover:text-slate-400 cursor-help"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <div
                      class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-slate-900 border 
                             border-slate-700 rounded-lg text-xs text-slate-300 whitespace-nowrap opacity-0 
                             invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 
                             z-50 shadow-lg max-w-xs"
                    >
                      {{ strategy.description || '暂无描述' }}
                      <div
                        class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent 
                               border-t-slate-900"
                      ></div>
                    </div>
                  </div>
                </div>

                <!-- Threshold Parameter Config -->
                <div class="mt-2 flex items-center gap-2">
                  <label class="text-xs text-slate-400">阈值:</label>
                  <input
                    type="number"
                    :value="strategyParams[strategy.id] ?? strategy.defaultThreshold ?? 0"
                    @input="(e) => updateThreshold(strategy.id, parseFloat((e.target as HTMLInputElement).value) || 0)"
                    @click.stop
                    class="w-20 px-2 py-1 text-sm bg-slate-700 border border-slate-600 rounded text-slate-200 
                           focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50"
                    placeholder="阈值"
                  />
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- Footer -->
        <div class="px-3 py-2 border-t border-slate-700 bg-slate-800/80 flex justify-end">
          <button
            type="button"
            @click="closeDropdown"
            class="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg 
                   transition-colors"
          >
            确定
          </button>
        </div>
      </div>
    </Transition>

    <!-- Backdrop -->
    <div
      v-if="isOpen"
      class="fixed inset-0 z-40"
      @click="closeDropdown"
    ></div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.5);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.7);
}
</style>
