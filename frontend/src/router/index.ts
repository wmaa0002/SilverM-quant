import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SignalsView from '../views/SignalsView.vue'
import PositionsView from '../views/PositionsView.vue'
import AgentView from '../views/AgentView.vue'
import DataUpdateView from '../views/DataUpdateView.vue'
import MultiSignalResonanceView from '../views/MultiSignalResonanceView.vue'
import BacktestDetail from '../views/BacktestDetail.vue'
import BacktestDashboard from '../views/BacktestDashboard.vue'
import StrategyManagement from '../views/StrategyManagement.vue'
import TradingSignalsView from '../views/TradingSignalsView.vue'
import HistoryAnalysisView from '../views/HistoryAnalysisView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/trading-signals',
      name: 'trading-signals',
      component: TradingSignalsView
    },
    {
      path: '/signals',
      name: 'signals',
      component: SignalsView
    },
    {
      path: '/positions',
      name: 'positions',
      component: PositionsView
    },
    {
      path: '/agent',
      name: 'agent',
      component: AgentView
    },
    {
      path: '/data-update',
      name: 'data-update',
      component: DataUpdateView
    },
    {
      path: '/multi-signal-resonance',
      name: 'multi-signal-resonance',
      component: MultiSignalResonanceView
    },
    {
      path: '/backtest-history',
      name: 'backtest-history',
      component: BacktestDashboard
    },
    {
      path: '/backtest/:runId',
      name: 'backtest-detail',
      component: BacktestDetail
    },
    {
      path: '/backtest-dashboard',
      name: 'backtest-dashboard',
      component: BacktestDashboard
    },
    {
      path: '/strategy-management',
      name: 'strategy-management',
      component: StrategyManagement
    },
    {
      path: '/history-analysis',
      name: 'history-analysis',
      component: HistoryAnalysisView
    }
  ]
})

export default router
