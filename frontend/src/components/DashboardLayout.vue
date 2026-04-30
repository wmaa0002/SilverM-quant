<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', label: '首页', icon: 'home' },
  { path: '/signals', label: '信号', icon: 'signal' },
  { path: '/multi-signal-resonance', label: '多策略共振', icon: 'chart' },
  { path: '/backtest-dashboard', label: '回测仪表盘', icon: 'dashboard' },
  { path: '/agent', label: '多Agent分析', icon: 'agent' },
  { path: '/data-update', label: '数据更新', icon: 'database' },
]

const isActive = (path: string) => {
  if (path === '/') return route.path === '/'
  if (path.startsWith('/backtest')) return route.path.startsWith('/backtest')
  if (path.startsWith('/signal')) return route.path.startsWith('/signal')
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="min-h-svh bg-slate-900 text-white relative">
    <header class="fixed left-0 top-0 right-0 z-50 h-16 flex flex-row items-center px-6 w-full bg-slate-900/95 border-b border-slate-700/50 backdrop-blur-md">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg flex-shrink-0">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
          </svg>
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">SilverQuant</h1>
          <p class="text-xs text-slate-400" id="updateTime"></p>
        </div>
      </div>

      <nav class="absolute left-1/2 -translate-x-1/2 flex items-center gap-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'nav-link flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer overflow-hidden text-sm',
            isActive(item.path) 
              ? 'bg-blue-500/20 border border-blue-500 text-blue-400' 
              : 'hover:bg-slate-700/50 border border-slate-600'
          ]"
        >
          {{ item.label }}
        </router-link>
      </nav>

      <div class="ml-auto flex items-center gap-2">
        <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
        <span class="text-emerald-400 text-sm font-medium">实时</span>
      </div>
    </header>

    <main class="px-6 pt-16">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.glass-card {
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid #334155;
  border-radius: 12px;
}

main {
  min-height: 100svh;
}

.nav-link.active {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}
</style>
