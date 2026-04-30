<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

interface AnalysisResult {
  symbol: string
  name?: string
  analysis_date: string
  final_decision?: string
  confidence?: number
  bull_confidence?: number
  bear_confidence?: number
  bull_research?: string
  bear_research?: string
  reports?: {
    market?: string
    news?: string
    fundamentals?: string
  }
  trading_signal?: {
    entry_price?: number
    stop_loss?: number
    take_profit?: number
    position_size?: number
  }
  debate_result?: {
    conservative_view: { confidence: number; recommended_position: number; arguments: string[]; risk_points: string[] }
    neutral_view: { confidence: number; recommended_position: number; arguments: string[]; risk_points: string[] }
    aggressive_view: { confidence: number; recommended_position: number; arguments: string[]; risk_points: string[] }
    final_risk_level: string
    recommended_position: number
    consensus: string
  }
  research?: {
    recommendation: string
    confidence: number
    reasoning: string
    key_points: string[]
  }
  risk?: {
    risk_level: string
    risk_score: number
    stop_loss: number
    position_size: number
  }
}

const symbol = ref('')
const tradeDate = ref(new Date().toISOString().split('T')[0])
const analyzing = ref(false)
const result = ref<AnalysisResult | null>(null)
const error = ref('')
const researchExpanded = ref(false)

const analyze = async () => {
  if (!symbol.value) {
    error.value = '请输入股票代码'
    return
  }
  
  analyzing.value = true
  error.value = ''
  result.value = null
  
  try {
    const response = await axios.post('/api/agent/analyze', {
      symbol: symbol.value,
      trade_date: tradeDate.value
    })
    result.value = response.data
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '分析失败'
  } finally {
    analyzing.value = false
  }
}

const getDecisionClass = (decision: string | undefined) => {
  if (!decision) return 'decision-hold'
  if (decision.includes('买')) return 'decision-buy'
  if (decision.includes('卖')) return 'decision-sell'
  return 'decision-hold'
}

const getConfidenceClass = (confidence: number | undefined) => {
  if (!confidence) return 'confidence-medium'
  if (confidence > 0.6) return 'confidence-high'
  if (confidence >= 0.4) return 'confidence-medium'
  return 'confidence-low'
}

const getRiskBadgeClass = (level: string | undefined) => {
  if (!level) return 'bg-slate-500/20 text-slate-400'
  if (level === 'LOW') return 'bg-green-500/20 text-green-400'
  if (level === 'HIGH') return 'bg-red-500/20 text-red-400'
  return 'bg-yellow-500/20 text-yellow-400'
}

const getDebaterIcon = (type: string) => {
  if (type === 'conservative') return '🛡️'
  if (type === 'neutral') return '⚖️'
  return '🚀'
}

const getDebaterTitle = (type: string) => {
  if (type === 'conservative') return '保守派'
  if (type === 'neutral') return '中立派'
  return '激进派'
}
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <!-- Header -->
    <header class="mb-6 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <router-link to="/" class="flex items-center gap-2 text-slate-400 hover:text-white transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
          </svg>
          <span class="text-sm">返回首页</span>
        </router-link>
      </div>
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
          </svg>
        </div>
        <div>
          <h1 class="text-2xl font-bold">多Agent智能股票分析</h1>
          <p class="text-sm text-slate-400">Multi-Agent Stock Analysis</p>
        </div>
      </div>
      <div class="w-20"></div>
    </header>
    
    <!-- Input Form -->
    <div class="glass-card p-6 mb-6 animate-fade-in" style="animation-delay: 0.1s">
      <div class="flex flex-col md:flex-row gap-4">
        <div class="flex-1">
          <label class="block text-sm text-slate-400 mb-2">股票代码</label>
          <input
            v-model="symbol"
            type="text"
            placeholder="600519"
            class="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
            @keyup.enter="analyze"
          />
        </div>
        <div class="flex-1">
          <label class="block text-sm text-slate-400 mb-2">分析日期</label>
          <input
            v-model="tradeDate"
            type="date"
            class="w-full px-4 py-3 bg-slate-800/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
          />
        </div>
        <div class="flex items-end">
          <button
            @click="analyze"
            :disabled="analyzing || !symbol"
            class="px-8 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition-all transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {{ analyzing ? '分析中...' : '开始分析' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Loading State -->
    <div v-if="analyzing" class="glass-card p-12 mb-6 text-center">
      <div class="flex flex-col items-center gap-4">
        <svg class="w-16 h-16 text-blue-500 spinner" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
        <p class="text-xl text-slate-300">分析中...</p>
        <p class="text-sm text-slate-500">AI正在整合多维度信息，请稍候</p>
      </div>
    </div>
    
    <!-- Results Section -->
    <div v-if="result && !analyzing" class="space-y-6">
      <!-- Decision Card -->
      <div class="glass-card p-8 text-center animate-fade-in" style="animation-delay: 0.1s">
        <p class="text-slate-400 text-sm mb-2">最终决策</p>
        <p class="text-5xl font-bold tracking-wide" :class="getDecisionClass(result.final_decision)">
          {{ result.final_decision || '-' }}
        </p>
        <p class="text-slate-500 text-sm mt-2">Final Decision</p>
      </div>
      
      <!-- Confidence Bar -->
      <div class="glass-card p-6 animate-fade-in" style="animation-delay: 0.15s">
        <div class="flex justify-between items-center mb-3">
          <p class="text-slate-400 text-sm">置信度</p>
          <p class="text-slate-300 font-medium">{{ result.confidence ? (result.confidence * 100).toFixed(0) + '%' : '0%' }}</p>
        </div>
        <div class="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-500"
            :class="getConfidenceClass(result.confidence)"
            :style="{ width: (result.confidence || 0) * 100 + '%' }"
          ></div>
        </div>
      </div>

      <!-- Task 9: Bull/Bear Confidence Bars -->
      <div v-if="result.bull_confidence !== undefined || result.bear_confidence !== undefined" 
           class="glass-card p-6 animate-fade-in" style="animation-delay: 0.17s">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
          </svg>
          多空信心指数 Bull/Bear Confidence
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div class="flex justify-between mb-1">
              <span class="text-green-400">🟢 多头置信度</span>
              <span class="text-slate-300 font-medium">{{ ((result.bull_confidence || 0) * 100).toFixed(0) }}%</span>
            </div>
            <div class="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
              <div class="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all duration-500"
                   :style="{ width: ((result.bull_confidence || 0) * 100) + '%' }"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between mb-1">
              <span class="text-red-400">🔴 空头置信度</span>
              <span class="text-slate-300 font-medium">{{ ((result.bear_confidence || 0) * 100).toFixed(0) }}%</span>
            </div>
            <div class="w-full bg-slate-700 rounded-full h-3 overflow-hidden">
              <div class="h-full bg-gradient-to-r from-red-500 to-rose-400 rounded-full transition-all duration-500"
                   :style="{ width: ((result.bear_confidence || 0) * 100) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Trading Signal Card -->
      <div class="glass-card p-6 animate-fade-in" style="animation-delay: 0.2s">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
          </svg>
          交易信号 Trading Signal
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="signal-value">
            <p class="signal-label">入场价 Entry</p>
            <p class="signal-number text-green-400">{{ result.trading_signal?.entry_price || '-' }}</p>
          </div>
          <div class="signal-value">
            <p class="signal-label">止损价 Stop Loss</p>
            <p class="signal-number text-red-400">{{ result.trading_signal?.stop_loss || '-' }}</p>
          </div>
          <div class="signal-value">
            <p class="signal-label">止盈价 Take Profit</p>
            <p class="signal-number text-blue-400">{{ result.trading_signal?.take_profit || '-' }}</p>
          </div>
          <div class="signal-value">
            <p class="signal-label">仓位 Position</p>
            <p class="signal-number text-purple-400">
              {{ result.trading_signal?.position_size ? (result.trading_signal.position_size * 100).toFixed(0) + '%' : '-' }}
            </p>
          </div>
        </div>
      </div>

      <!-- Task 10: Three Debaters View -->
      <div v-if="result.debate_result" class="glass-card p-6 animate-fade-in" style="animation-delay: 0.25s">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
          </svg>
          三方辩论观点 Three Debaters View
        </h3>
        
        <!-- Debater Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <!-- Conservative -->
          <div class="glass-card p-4 border-l-4 border-l-blue-400 bg-slate-800/30">
            <h4 class="font-bold text-blue-400 mb-3 flex items-center gap-2">
              <span class="text-xl">{{ getDebaterIcon('conservative') }}</span>
              {{ getDebaterTitle('conservative') }}
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">置信度:</span>
                <span class="text-slate-200 font-medium">
                  {{ ((result.debate_result.conservative_view.confidence || 0) * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">推荐仓位:</span>
                <span class="text-slate-200 font-medium">
                  {{ ((result.debate_result.conservative_view.recommended_position || 0) * 100).toFixed(0) }}%
                </span>
              </div>
              <div v-if="result.debate_result.conservative_view.arguments?.length" class="mt-3">
                <p class="text-slate-400 mb-1">论点:</p>
                <ul class="list-disc list-inside text-slate-300 space-y-1">
                  <li v-for="(arg, idx) in result.debate_result.conservative_view.arguments" :key="idx" class="text-xs">
                    {{ arg }}
                  </li>
                </ul>
              </div>
              <div v-if="result.debate_result.conservative_view.risk_points?.length" class="mt-3">
                <p class="text-slate-400 mb-1">风险点:</p>
                <ul class="list-disc list-inside text-red-300/80 space-y-1">
                  <li v-for="(risk, idx) in result.debate_result.conservative_view.risk_points" :key="idx" class="text-xs">
                    {{ risk }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
          
          <!-- Neutral -->
          <div class="glass-card p-4 border-l-4 border-l-yellow-400 bg-slate-800/30">
            <h4 class="font-bold text-yellow-400 mb-3 flex items-center gap-2">
              <span class="text-xl">{{ getDebaterIcon('neutral') }}</span>
              {{ getDebaterTitle('neutral') }}
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">置信度:</span>
                <span class="text-slate-200 font-medium">
                  {{ ((result.debate_result.neutral_view.confidence || 0) * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">推荐仓位:</span>
                <span class="text-slate-200 font-medium">
                  {{ ((result.debate_result.neutral_view.recommended_position || 0) * 100).toFixed(0) }}%
                </span>
              </div>
              <div v-if="result.debate_result.neutral_view.arguments?.length" class="mt-3">
                <p class="text-slate-400 mb-1">论点:</p>
                <ul class="list-disc list-inside text-slate-300 space-y-1">
                  <li v-for="(arg, idx) in result.debate_result.neutral_view.arguments" :key="idx" class="text-xs">
                    {{ arg }}
                  </li>
                </ul>
              </div>
              <div v-if="result.debate_result.neutral_view.risk_points?.length" class="mt-3">
                <p class="text-slate-400 mb-1">风险点:</p>
                <ul class="list-disc list-inside text-red-300/80 space-y-1">
                  <li v-for="(risk, idx) in result.debate_result.neutral_view.risk_points" :key="idx" class="text-xs">
                    {{ risk }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
          
          <!-- Aggressive -->
          <div class="glass-card p-4 border-l-4 border-l-red-400 bg-slate-800/30">
            <h4 class="font-bold text-red-400 mb-3 flex items-center gap-2">
              <span class="text-xl">{{ getDebaterIcon('aggressive') }}</span>
              {{ getDebaterTitle('aggressive') }}
            </h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-slate-400">置信度:</span>
                <span class="text-slate-200 font-medium">
                  {{ ((result.debate_result.aggressive_view.confidence || 0) * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">推荐仓位:</span>
                <span class="text-slate-200 font-medium">
                  {{ ((result.debate_result.aggressive_view.recommended_position || 0) * 100).toFixed(0) }}%
                </span>
              </div>
              <div v-if="result.debate_result.aggressive_view.arguments?.length" class="mt-3">
                <p class="text-slate-400 mb-1">论点:</p>
                <ul class="list-disc list-inside text-slate-300 space-y-1">
                  <li v-for="(arg, idx) in result.debate_result.aggressive_view.arguments" :key="idx" class="text-xs">
                    {{ arg }}
                  </li>
                </ul>
              </div>
              <div v-if="result.debate_result.aggressive_view.risk_points?.length" class="mt-3">
                <p class="text-slate-400 mb-1">风险点:</p>
                <ul class="list-disc list-inside text-red-300/80 space-y-1">
                  <li v-for="(risk, idx) in result.debate_result.aggressive_view.risk_points" :key="idx" class="text-xs">
                    {{ risk }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Bottom Aggregation -->
        <div class="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div class="grid grid-cols-3 gap-4 text-center">
            <div>
              <p class="text-slate-400 text-xs mb-1">投票结果</p>
              <p class="text-white font-semibold">{{ result.debate_result.consensus || '-' }}</p>
            </div>
            <div>
              <p class="text-slate-400 text-xs mb-1">推荐仓位</p>
              <p class="text-purple-400 font-semibold">
                {{ result.debate_result.recommended_position !== undefined 
                    ? (result.debate_result.recommended_position * 100).toFixed(0) + '%' 
                    : '-' }}
              </p>
            </div>
            <div>
              <p class="text-slate-400 text-xs mb-1">风险等级</p>
              <span class="px-3 py-1 rounded-full text-sm font-semibold" :class="getRiskBadgeClass(result.debate_result.final_risk_level)">
                {{ result.debate_result.final_risk_level || '-' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Task 11: Research Manager Module -->
      <div v-if="result.research" class="glass-card p-6 animate-fade-in" style="animation-delay: 0.3s">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
          </svg>
          研究经理报告 Research Manager
        </h3>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Recommendation -->
          <div class="bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-lg p-4 border border-blue-500/30">
            <p class="text-slate-400 text-xs mb-2">投资建议 Recommendation</p>
            <p class="text-2xl font-bold text-white mb-2">{{ result.research.recommendation || '-' }}</p>
            <div class="flex items-center gap-2">
              <span class="text-slate-400 text-sm">置信度:</span>
              <span class="text-green-400 font-semibold">
                {{ result.research.confidence !== undefined ? (result.research.confidence * 100).toFixed(0) + '%' : '-' }}
              </span>
            </div>
          </div>
          
          <!-- Key Points -->
          <div class="bg-slate-800/30 rounded-lg p-4">
            <p class="text-slate-400 text-xs mb-3">关键要点 Key Points</p>
            <ul class="space-y-2" v-if="result.research.key_points?.length">
              <li v-for="(point, idx) in result.research.key_points" :key="idx" 
                  class="flex items-start gap-2 text-slate-300 text-sm">
                <span class="text-blue-400 mt-0.5">•</span>
                <span>{{ point }}</span>
              </li>
            </ul>
            <p v-else class="text-slate-500 text-sm">-</p>
          </div>
        </div>
        
        <!-- Reasoning with expand/collapse -->
        <div class="mt-4">
          <button 
            @click="researchExpanded = !researchExpanded"
            class="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-2"
          >
            <svg class="w-4 h-4 transition-transform" :class="{ 'rotate-90': researchExpanded }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
            <span class="text-sm">详细 reasoning</span>
            <span v-if="!researchExpanded && result.research.reasoning?.length > 200" class="text-xs text-slate-500">
              (点击展开)
            </span>
          </button>
          <div 
            class="bg-slate-800/20 rounded-lg p-4 text-slate-300 text-sm leading-relaxed"
            :class="{ 'max-h-32 overflow-hidden': !researchExpanded && result.research.reasoning?.length > 200 }"
          >
            <p class="whitespace-pre-wrap">{{ result.research.reasoning || '-' }}</p>
          </div>
          <button 
            v-if="!researchExpanded && result.research.reasoning?.length > 200"
            @click="researchExpanded = true"
            class="text-blue-400 text-xs hover:text-blue-300 mt-1"
          >
            显示全部
          </button>
        </div>
      </div>

      <!-- Task 12: Risk Manager Module -->
      <div v-if="result.risk" class="glass-card p-6 animate-fade-in" style="animation-delay: 0.35s">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg class="w-5 h-5 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
          </svg>
          风险管理 Risk Manager
        </h3>
        
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <!-- Risk Level Badge -->
          <div class="bg-slate-800/30 rounded-lg p-4 text-center">
            <p class="text-slate-400 text-xs mb-2">风险等级 Risk Level</p>
            <span 
              class="inline-block px-4 py-2 rounded-full text-lg font-bold"
              :class="getRiskBadgeClass(result.risk.risk_level)"
            >
              {{ result.risk.risk_level || '-' }}
            </span>
          </div>
          
          <!-- Risk Score -->
          <div class="bg-slate-800/30 rounded-lg p-4 text-center">
            <p class="text-slate-400 text-xs mb-2">风险评分 Risk Score</p>
            <p class="text-2xl font-bold text-orange-400">
              {{ result.risk.risk_score !== undefined ? result.risk.risk_score.toFixed(2) : '-' }}
            </p>
          </div>
          
          <!-- Stop Loss -->
          <div class="bg-slate-800/30 rounded-lg p-4 text-center">
            <p class="text-slate-400 text-xs mb-2">止损价 Stop Loss</p>
            <p class="text-2xl font-bold text-red-400">
              {{ result.risk.stop_loss || '-' }}
            </p>
          </div>
          
          <!-- Position Size -->
          <div class="bg-slate-800/30 rounded-lg p-4 text-center">
            <p class="text-slate-400 text-xs mb-2">仓位比例 Position Size</p>
            <p class="text-2xl font-bold text-purple-400">
              {{ result.risk.position_size !== undefined ? (result.risk.position_size * 100).toFixed(0) + '%' : '-' }}
            </p>
          </div>
        </div>
      </div>
      
      <!-- Research Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="glass-card p-6 research-bull animate-fade-in" style="animation-delay: 0.4s">
          <h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
            <svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
            </svg>
            多头研究 Bull Research
          </h3>
          <div class="bg-slate-800/30 rounded-lg p-4 min-h-[120px]">
            <p class="text-slate-300 leading-relaxed whitespace-pre-wrap">{{ result.bull_research || '-' }}</p>
          </div>
        </div>
        <div class="glass-card p-6 research-bear animate-fade-in" style="animation-delay: 0.45s">
          <h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
            <svg class="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0v-8m0 8l-8-8-4 4-6-6"></path>
            </svg>
            空头研究 Bear Research
          </h3>
          <div class="bg-slate-800/30 rounded-lg p-4 min-h-[120px]">
            <p class="text-slate-300 leading-relaxed whitespace-pre-wrap">{{ result.bear_research || '-' }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Error Display -->
    <div v-if="error" class="glass-card p-6 border-red-500/50">
      <div class="flex items-center gap-3 text-red-400">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <p class="font-medium">错误</p>
      </div>
      <p class="mt-3 text-slate-300">{{ error }}</p>
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

.decision-buy {
  color: #10b981;
}

.decision-hold {
  color: #eab308;
}

.decision-sell {
  color: #ef4444;
}

.confidence-high {
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
}

.confidence-medium {
  background: linear-gradient(90deg, #eab308 0%, #ca8a04 100%);
}

.confidence-low {
  background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%);
}

.research-bull {
  border-left: 4px solid #10b981;
}

.research-bear {
  border-left: 4px solid #ef4444;
}

.signal-value {
  background: rgba(59, 130, 246, 0.1);
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}

.signal-label {
  color: #94a3b8;
  font-size: 12px;
  margin-bottom: 4px;
}

.signal-number {
  font-size: 20px;
  font-weight: bold;
  color: #f1f5f9;
}

.animate-fade-in {
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.spinner {
  animation: spin 1s linear infinite;
}
</style>
