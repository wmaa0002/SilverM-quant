<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

interface TableStatus {
  [key: string]: {
    count: number
    latest: string
  }
}

const status = ref<TableStatus | null>(null)
const updating = ref(false)
const log = ref('')
const loading = ref(true)
const error = ref('')
const currentSource = ref<'tushare' | 'baostock'>('tushare')
const currentTaskId = ref<string | null>(null)
const taskProgress = ref(0)
const taskMessage = ref('')

const selectedUpdateType = ref('daily')
const startDate = ref('')
const endDate = ref('')
const workers = ref(4)

const tableNames: Record<string, string> = {
  'dwd_daily_price': '日线行情',
  'dwd_daily_basic': '每日指标',
  'dwd_adj_factor': '复权因子',
  'dwd_income': '利润表',
  'dwd_balancesheet': '资产负债表',
  'dwd_cashflow': '现金流量表',
  'dwd_index_daily': '指数日线',
  'dwd_stock_info': '股票基础信息',
  'dwd_trade_calendar': '交易日历'
}

const updateTypes = [
  { value: 'all', label: '全量更新', desc: '更新所有数据表' },
  { value: 'daily', label: '日线数据', desc: '日线行情数据' },
  { value: 'daily_basic', label: '每日指标', desc: 'PE、PB等每日指标' },
  { value: 'adj_factor', label: '复权因子', desc: '复权因子数据' },
  { value: 'index', label: '指数数据', desc: '沪深指数日线数据' },
  { value: 'stock_info', label: '股票信息', desc: '股票基础信息' },
  { value: 'trade_calendar', label: '交易日历', desc: '交易日历' },
  { value: 'financial', label: '财务数据', desc: '财报数据(多进程)' }
]

const fetchStatus = async () => {
  try {
    loading.value = true
    error.value = ''
    const response = await axios.get('/api/data-update/status')
    if (response.data.success) {
      status.value = response.data.data
    }
  } catch (e) {
    error.value = '获取状态失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

const startUpdate = async () => {
  updating.value = true
  error.value = ''
  taskProgress.value = 0
  taskMessage.value = ''
  
  try {
    const response = await axios.post('/api/data-update/update', {
      data_type: selectedUpdateType.value,
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
      workers: workers.value,
      source: currentSource.value
    })
    if (response.data.success) {
      currentTaskId.value = response.data.task_id
      pollTask()
    } else {
      error.value = response.data.error || '启动失败'
    }
  } catch (e: any) {
    error.value = e.response?.data?.error || '触发更新失败'
    console.error(e)
  } finally {
    updating.value = false
  }
}

const pollTask = async () => {
  if (!currentTaskId.value) return
  
  try {
    const response = await axios.get(`/api/data-update/task/${currentTaskId.value}`)
    if (response.data.success) {
      const task = response.data.data
      taskProgress.value = task.progress || 0
      taskMessage.value = task.message || ''
      
      if (task.status === 'completed' || task.status === 'error') {
        currentTaskId.value = null
        fetchStatus()
        fetchLog()
      } else {
        setTimeout(pollTask, 2000)
      }
    }
  } catch (e) {
    console.error(e)
    setTimeout(pollTask, 5000)
  }
}

const fetchLog = async (lines = 50) => {
  try {
    const response = await axios.get(`/api/data-update/log?lines=${lines}`)
    if (response.data.success) {
      log.value = response.data.log || ''
    }
  } catch (e) {
    console.error(e)
  }
}

const toggleSource = () => {
  currentSource.value = currentSource.value === 'tushare' ? 'baostock' : 'tushare'
}

const getCountClass = (count: number) => {
  if (count > 10000) return 'count-high'
  if (count > 0) return 'count-low'
  return 'count-empty'
}

onMounted(() => {
  fetchStatus()
  fetchLog()
})
</script>

<template>
  <div class="min-h-screen" style="background: #0f1419; color: #e7e9ea;">
    <!-- Header -->
    <header class="header">
      <h1>📊 数据更新中心</h1>
      <nav class="nav">
        <router-link to="/">持仓</router-link>
        <router-link to="/agent">分析</router-link>
        <router-link to="/signals">信号</router-link>
        <router-link to="/data-update" class="active">数据更新</router-link>
      </nav>
    </header>
    
    <div class="container">
      <!-- Data Table Status -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">📋 DWD层数据表状态</h2>
          <button class="refresh-btn" @click="fetchStatus">🔄 刷新状态</button>
        </div>
        <table class="table-status">
          <thead>
            <tr>
              <th>表名</th>
              <th>说明</th>
              <th>记录数</th>
              <th>最新日期</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" style="text-align:center;color:#8b98a5">加载中...</td>
            </tr>
            <tr v-else-if="!status">
              <td colspan="5" style="text-align:center;color:#8b98a5">暂无数据</td>
            </tr>
            <tr v-for="(info, table in status" :key="table">
              <td><code>{{ table }}</code></td>
              <td>{{ tableNames[table] || table }}</td>
              <td :class="'status-count ' + getCountClass(info.count)">{{ info.count.toLocaleString() }}</td>
              <td>{{ info.latest || '-' }}</td>
              <td>
                <span :class="'status-dot ' + (info.count > 0 ? 'has-data' : 'no-data')"></span>
                {{ info.count > 0 ? '有数据' : '空表' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- Update Operation -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">⚡ 触发数据更新</h2>
          <div class="source-switch">
            <span :class="{ active: currentSource === 'tushare' }">Tushare</span>
            <div :class="['switch', currentSource]" @click="toggleSource"></div>
            <span :class="{ active: currentSource === 'baostock' }">Baostock</span>
          </div>
        </div>
        
        <div class="form-section">
          <div class="form-group">
            <h3>📌 选择数据表</h3>
            <select v-model="selectedUpdateType" class="select-input">
              <option v-for="type in updateTypes" :key="type.value" :value="type.value">
                {{ type.label }} - {{ type.desc }}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <h3>📅 时间范围</h3>
            <div class="date-inputs">
              <div class="date-field">
                <label>开始日期</label>
                <input type="date" v-model="startDate" class="date-input" placeholder="20240101" />
              </div>
              <div class="date-field">
                <label>结束日期</label>
                <input type="date" v-model="endDate" class="date-input" />
              </div>
            </div>
            <p class="hint">留空则自动使用合理默认值</p>
          </div>
          
          <div class="form-group">
            <h3>⚙️ 并行进程数</h3>
            <input type="number" v-model.number="workers" min="1" max="16" class="workers-input" />
            <p class="hint">建议4-8进程，太多可能导致API限流</p>
          </div>
          
          <div class="form-group">
            <h3>📌 触发更新</h3>
            <div class="btn-group">
              <button class="btn btn-primary" @click="startUpdate" :disabled="updating">
                {{ updating ? '更新中...' : '🚀 开始更新' }}
              </button>
              <button class="btn btn-secondary" @click="fetchStatus">🔄 刷新状态</button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Task Status -->
      <div v-if="currentTaskId" class="card">
        <div class="card-header">
          <h2 class="card-title">📊 更新任务状态</h2>
        </div>
        <div class="task-status">
          <span class="task-id">{{ currentTaskId }}</span>
          <span class="task-message">{{ taskMessage || '-' }}</span>
          <span class="task-progress">{{ taskProgress }}%</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: taskProgress + '%' }"></div>
        </div>
      </div>
      
      <!-- Logs and Instructions -->
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">📜 更新日志</h2>
            <button class="refresh-btn" @click="fetchLog(100)">🔄 刷新日志</button>
          </div>
          <div class="log-container">
            <div v-if="!log" class="log-line">点击刷新获取日志...</div>
            <div v-else v-for="(line, i) in log.split('\n').slice(-30)" :key="i" :class="['log-line', line.includes('ERROR') ? 'error' : line.includes('WARNING') || line.includes('失败') ? 'warning' : '']">
              {{ line }}
            </div>
          </div>
        </div>
        
        <div class="card">
          <div class="card-header">
            <h2 class="card-title">💡 使用说明</h2>
          </div>
          <div style="font-size:13px;line-height:1.8;color:#8b98a5;">
            <p><strong>增量更新:</strong> 自动从上次更新到的日期继续，适合每日例行更新</p>
            <p><strong>全量更新:</strong> 从指定日期开始更新所有数据</p>
            <p><strong>并行模式:</strong> 使用多进程加速下载，但需注意API限流</p>
            <p style="margin-top:12px;"><strong>推荐流程:</strong></p>
            <ol style="margin-left:20px;">
              <li>首次: 选择 <code>全量更新</code> + <code>all</code></li>
              <li>日常: 选择 <code>增量更新</code> + <code>daily</code></li>
              <li>财务: 每季度报告发布后更新</li>
            </ol>
            <p style="margin-top:12px;color:#f59e0b;">⚠️ 全量更新耗时较长，建议在非交易时间执行</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.header {
  background: #1a1f25;
  padding: 16px 24px;
  border-bottom: 1px solid #2f3336;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
}

.nav {
  display: flex;
  gap: 24px;
}

.nav a {
  color: #8b98a5;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.nav a:hover, .nav a.active {
  color: #1d9bf0;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.card {
  background: #1a1f25;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid #2f3336;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #e7e9ea;
}

.refresh-btn {
  background: #2f3336;
  border: none;
  color: #e7e9ea;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.refresh-btn:hover {
  background: #3f4346;
}

.table-status {
  width: 100%;
  border-collapse: collapse;
}

.table-status th, .table-status td {
  text-align: left;
  padding: 12px;
  border-bottom: 1px solid #2f3336;
  font-size: 13px;
}

.table-status th {
  color: #8b98a5;
  font-weight: 500;
}

.table-status tr:hover {
  background: #1f2937;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}

.status-dot.has-data {
  background: #00ba7c;
}

.status-dot.no-data {
  background: #f4212e;
}

.status-count {
  font-weight: 600;
}

.status-count.count-high {
  color: #00ba7c;
}

.status-count.count-low {
  color: #f59e0b;
}

.status-count.count-empty {
  color: #8b98a5;
}

.form-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.form-group {
  background: #252a30;
  padding: 16px;
  border-radius: 8px;
}

.form-group h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #e7e9ea;
}

.select-input {
  width: 100%;
  padding: 10px 14px;
  background: #1a1f25;
  border: 1px solid #2f3336;
  border-radius: 6px;
  color: #e7e9ea;
  font-size: 14px;
  cursor: pointer;
  appearance: none;
}

.select-input:focus {
  outline: none;
  border-color: #1d9bf0;
}

.date-inputs {
  display: flex;
  gap: 12px;
}

.date-field {
  flex: 1;
}

.date-field label {
  display: block;
  font-size: 12px;
  color: #8b98a5;
  margin-bottom: 6px;
}

.date-input {
  width: 100%;
  padding: 8px 12px;
  background: #1a1f25;
  border: 1px solid #2f3336;
  border-radius: 6px;
  color: #e7e9ea;
  font-size: 13px;
}

.date-input:focus {
  outline: none;
  border-color: #1d9bf0;
}

.workers-input {
  width: 100%;
  padding: 8px 12px;
  background: #1a1f25;
  border: 1px solid #2f3336;
  border-radius: 6px;
  color: #e7e9ea;
  font-size: 13px;
}

.workers-input:focus {
  outline: none;
  border-color: #1d9bf0;
}

.hint {
  font-size: 11px;
  color: #6e7681;
  margin-top: 6px;
}

.btn-group {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #1d9bf0;
  color: #fff;
}

.btn-primary:hover {
  background: #1a8cd8;
}

.btn-secondary {
  background: #2f3336;
  color: #e7e9ea;
}

.btn-secondary:hover {
  background: #3f4346;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.progress-bar {
  height: 8px;
  background: #2f3336;
  border-radius: 4px;
  overflow: hidden;
  margin-top: 12px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1d9bf0, #00ba7c);
  border-radius: 4px;
  transition: width 0.3s;
}

.task-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #252a30;
  border-radius: 8px;
  margin-bottom: 12px;
}

.task-id {
  font-family: monospace;
  font-size: 12px;
  color: #8b98a5;
}

.task-message {
  flex: 1;
  font-size: 13px;
}

.task-progress {
  font-size: 12px;
  color: #00ba7c;
  font-weight: 600;
}

.log-container {
  background: #0d1117;
  border-radius: 8px;
  padding: 16px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #8b949e;
}

.log-line {
  margin-bottom: 4px;
}

.log-line.error {
  color: #f85149;
}

.log-line.warning {
  color: #d29922;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 1024px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }
}

.source-switch {
  display: flex;
  align-items: center;
  gap: 12px;
}

.source-switch span {
  font-size: 14px;
  color: #8b98a5;
  min-width: 60px;
}

.source-switch span.active {
  color: #1d9bf0;
  font-weight: 600;
}

.switch {
  position: relative;
  width: 56px;
  height: 28px;
  background: #2f3336;
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.3s;
}

.switch::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 24px;
  height: 24px;
  background: #e7e9ea;
  border-radius: 50%;
  transition: transform 0.3s;
}

.switch.baostock {
  background: #1d9bf0;
}

.switch.baostock::after {
  transform: translateX(28px);
}
</style>
