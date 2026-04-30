import { defineStore } from 'pinia'
import axios from 'axios'
import { ref, computed } from 'vue'

export interface Strategy {
  name: string
  description?: string
  threshold_required?: boolean
  min_data_days?: number
}

export interface BacktestParams {
  strategy_name: string
  start_date: string
  end_date: string
  stock_list?: string[]
  initial_capital?: number
}

export interface PerformanceMetrics {
  total_return: number
  annual_return: number
  benchmark_return: number
  excess_return: number
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  max_drawdown: number
  max_drawdown_duration: number
  volatility: number
  win_rate: number
  profit_loss_ratio: number
  total_trades: number
}

export interface BacktestResult {
  run_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  metrics?: PerformanceMetrics
  error?: string | null
}

// 批量回测结果接口
export interface BatchBacktestResult {
  task_id: string
  total_stocks: number
  success_count: number
  fail_count: number
  no_data_count: number
  success_rate: number
  avg_return: number
  avg_sharpe: number
  avg_win_rate: number
  avg_annual_return: number
  avg_max_drawdown: number
  total_trades: number
  top5_stocks: any[]
  bottom5_stocks: any[]
  param_results?: any[]
  stocks: any[]
}

export const useBacktestStore = defineStore('backtest', () => {
  // State
  const strategies = ref<Strategy[]>([])
  const selectedStrategies = ref<string[]>([])
  const startDate = ref<string>('')
  const endDate = ref<string>('')
  const stockSelectionMode = ref<'all' | 'single' | 'multiple'>('all')
  const selectedStocks = ref<string[]>([])
  const initialCapital = ref<number>(1000000)
  const isLoading = ref(false)
  const currentResult = ref<BacktestResult | null>(null)
  const error = ref<string | null>(null)

  // Batch backtest state
  const batchTaskId = ref<string | null>(null)
  const batchPollInterval = ref<number | null>(null)
  const batchStatus = ref<'idle' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'>('idle')
  const batchProgress = ref<number>(0)
  const batchMessage = ref<string>('')
  const batchResult = ref<BatchBacktestResult | null>(null)
  const batchError = ref<string | null>(null)

  // Getters
  const hasResult = computed(() => currentResult.value !== null && currentResult.value.status === 'completed')
  const isRunning = computed(() => isLoading.value)

  // Batch getters
  const isBatchRunning = computed(() => batchStatus.value === 'running' || batchStatus.value === 'pending')
  const hasBatchResult = computed(() => batchResult.value !== null && batchStatus.value === 'completed')

  // Actions
  async function fetchStrategies() {
    try {
      isLoading.value = true
      error.value = null
      const response = await axios.get('/api/backtest/strategies')
      // API 返回字符串数组，需要转换为 Strategy 对象
      strategies.value = (response.data.strategies || []).map((name: string) => ({ name }))
    } catch (e) {
      error.value = '获取策略列表失败'
      console.error('Failed to fetch strategies:', e)
    } finally {
      isLoading.value = false
    }
  }

  async function runBacktest() {
    if (selectedStrategies.value.length === 0) {
      error.value = '请至少选择一个策略'
      return
    }

    if (!startDate.value || !endDate.value) {
      error.value = '请选择日期范围'
      return
    }

    try {
      isLoading.value = true
      error.value = null
      currentResult.value = { run_id: '', status: 'running' }

      const params: BacktestParams = {
        strategy_name: selectedStrategies.value[0], // API expects single strategy name
        start_date: startDate.value.replace(/-/g, ''),
        end_date: endDate.value.replace(/-/g, ''),
        initial_capital: initialCapital.value
      }

      if (stockSelectionMode.value === 'single' && selectedStocks.value.length > 0) {
        params.stock_list = [selectedStocks.value[0]]
      } else if (stockSelectionMode.value === 'multiple' && selectedStocks.value.length > 0) {
        params.stock_list = selectedStocks.value
      }

      const response = await axios.post('/api/backtest/run', params)

      currentResult.value = {
        run_id: response.data.run_id,
        status: response.data.status || 'completed',
        metrics: response.data.metrics,
        error: response.data.error
      }
    } catch (e: any) {
      error.value = e.response?.data?.error || '回测运行失败'
      currentResult.value = {
        run_id: '',
        status: 'failed',
        error: error.value
      }
      console.error('Failed to run backtest:', e)
    } finally {
      isLoading.value = false
    }
  }

  // 轮询批量回测任务状态
  function pollBatchTask() {
    if (!batchTaskId.value) return

    const poll = async () => {
      try {
        const response = await axios.get(`/api/backtest/batch-task/${batchTaskId.value}`)
        const data = response.data

        batchStatus.value = data.status
        batchProgress.value = data.progress
        batchMessage.value = data.message

        if (data.status === 'completed') {
          // 获取最终结果
          const resultRes = await axios.get(`/api/backtest/batch-results/${batchTaskId.value}`)
          batchResult.value = resultRes.data
          batchStatus.value = 'completed'
          batchProgress.value = 100
          batchMessage.value = '回测完成'
          stopPolling()
        } else if (data.status === 'failed') {
          batchError.value = data.error_message || '回测失败'
          batchStatus.value = 'failed'
          stopPolling()
        }
      } catch (e: any) {
        console.error('轮询失败:', e)
        batchError.value = e.response?.data?.error || '轮询失败'
        batchStatus.value = 'failed'
        stopPolling()
      }
    }

    // 每2秒轮询
    batchPollInterval.value = window.setInterval(poll, 2000)

    // 30分钟超时
    window.setTimeout(() => {
      if (batchStatus.value === 'running' || batchStatus.value === 'pending') {
        batchError.value = '回测超时（30分钟）'
        batchStatus.value = 'failed'
        stopPolling()
      }
    }, 30 * 60 * 1000)
  }

  // 停止轮询
  function stopPolling() {
    if (batchPollInterval.value !== null) {
      clearInterval(batchPollInterval.value)
      batchPollInterval.value = null
    }
  }

  // 取消批量回测任务
  async function cancelBatchBacktest() {
    if (!batchTaskId.value) return

    try {
      await axios.delete(`/api/backtest/batch-task/${batchTaskId.value}`)
      batchStatus.value = 'cancelled'
      batchMessage.value = '任务已取消'
      stopPolling()
    } catch (e: any) {
      console.error('取消任务失败:', e)
    }
  }

  // 提交批量回测任务
  async function submitBatchBacktest(paramGrid?: string) {
    if (selectedStrategies.value.length === 0) {
      batchError.value = '请至少选择一个策略'
      return
    }

    if (!startDate.value || !endDate.value) {
      batchError.value = '请选择日期范围'
      return
    }

    try {
      batchError.value = null
      batchResult.value = null
      batchProgress.value = 0
      batchMessage.value = '提交回测任务...'

      const params: any = {
        strategy_name: selectedStrategies.value[0],
        start_date: startDate.value.replace(/-/g, ''),
        end_date: endDate.value.replace(/-/g, ''),
        initial_capital: initialCapital.value
      }

      // 如果不是全部股票，添加股票列表
      if (stockSelectionMode.value !== 'all' && selectedStocks.value.length > 0) {
        params.stock_list = selectedStocks.value
      }

      if (paramGrid) {
        params.param_grid = paramGrid
      }

      const response = await axios.post('/api/backtest/batch-run', params)

      batchTaskId.value = response.data.task_id
      batchStatus.value = 'pending'
      batchMessage.value = '任务已提交...'

      // 开始轮询
      pollBatchTask()
    } catch (e: any) {
      batchError.value = e.response?.data?.error || '提交失败'
      batchStatus.value = 'failed'
      console.error('提交批量回测失败:', e)
    }
  }

  // 重置批量回测状态
  function resetBatchResult() {
    stopPolling()
    batchTaskId.value = null
    batchStatus.value = 'idle'
    batchProgress.value = 0
    batchMessage.value = ''
    batchResult.value = null
    batchError.value = null
  }

  function resetResult() {
    currentResult.value = null
    error.value = null
  }

  function setDateRange(start: string, end: string) {
    startDate.value = start
    endDate.value = end
  }

  function setSelectedStrategies(stra: string[]) {
    selectedStrategies.value = stra
  }

  function setStockSelection(mode: 'all' | 'single' | 'multiple', stocks: string[] = []) {
    stockSelectionMode.value = mode
    selectedStocks.value = stocks
  }

  return {
    // State
    strategies,
    selectedStrategies,
    startDate,
    endDate,
    stockSelectionMode,
    selectedStocks,
    initialCapital,
    isLoading,
    currentResult,
    error,
    // Getters
    hasResult,
    isRunning,
    // Actions
    fetchStrategies,
    runBacktest,
    resetResult,
    setDateRange,
    setSelectedStrategies,
    setStockSelection,
    // Batch exports
    batchTaskId,
    batchStatus,
    batchProgress,
    batchMessage,
    batchResult,
    batchError,
    isBatchRunning,
    hasBatchResult,
    submitBatchBacktest,
    resetBatchResult,
    stopPolling,
    cancelBatchBacktest
  }
})