import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import BacktestDetail from '../BacktestDetail.vue'

const mockBatchDetail = {
  run_id: 'batch_20260428214135',
  type: 'batch' as const,
  total_stocks: 50,
  success_count: 45,
  success_rate: 0.9,
  total_trades: 150,
  metrics: {
    total_return: 0.15,
    annualized_return: 0.223,
    benchmark_return: 0.08,
    excess_return: 0.143,
    volatility: 0.121,
    max_drawdown: -0.072,
    max_drawdown_duration: 30,
    sharpe_ratio: 1.85,
    sortino_ratio: 2.22,
    calmar_ratio: 3.1,
    win_rate: 0.65,
    profit_loss_ratio: 1.86,
    total_trades: 150,
    total_profit: 125000,
    cumulative_return: 0.155,
    avg_drawdown: 0.045,
    expectancy: 0.0085,
    expectancy_r: null,
    best_trade: null,
    worst_trade: null,
    avg_profit: null,
    avg_loss: null,
    avg_holding_days: null
  },
  stocks: []
}

const mockSingleDetail = {
  run_id: 'single_20260428214135',
  type: 'single' as const,
  total_stocks: 1,
  trades: [],
  daily_pnl: [],
  metrics: {
    total_return: 0.12,
    annualized_return: 0.18,
    benchmark_return: 0.05,
    excess_return: 0.07,
    volatility: 0.15,
    max_drawdown: -0.1,
    max_drawdown_duration: 45,
    sharpe_ratio: 1.2,
    sortino_ratio: 1.5,
    calmar_ratio: 1.8,
    win_rate: 0.55,
    profit_loss_ratio: 1.5,
    total_trades: 50,
    total_profit: null,
    cumulative_return: null,
    avg_drawdown: null,
    expectancy: null,
    expectancy_r: null,
    best_trade: null,
    worst_trade: null,
    avg_profit: null,
    avg_loss: null,
    avg_holding_days: null
  }
}

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/backtest/history', component: { template: '<div>History</div>' } }]
})

describe('BacktestDetail Batch Metrics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should have correct Metrics interface fields', () => {
    const wrapper = mount(BacktestDetail, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': true,
          Line: { template: '<div class="chart-mock"></div>' },
          Bar: { template: '<div class="chart-mock"></div>' }
        }
      }
    })

    expect(wrapper.exists()).toBe(true)
  })

  it('should display batch metrics when isBatch is true', async () => {
    const wrapper = mount(BacktestDetail, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': true,
          Line: { template: '<div class="chart-mock"></div>' },
          Bar: { template: '<div class="chart-mock"></div>' }
        }
      }
    })

    await wrapper.vm.$nextTick()

    const vm = wrapper.vm as any
    expect(vm.isBatch).toBe(false)

    vm.detail = mockBatchDetail
    await wrapper.vm.$nextTick()

    expect(vm.isBatch).toBe(true)
    expect(wrapper.text()).toContain('总股票数')
    expect(wrapper.text()).toContain('50')
    expect(wrapper.text()).toContain('成功')
    expect(wrapper.text()).toContain('45')
    expect(wrapper.text()).toContain('总交易次数')
    expect(wrapper.text()).toContain('150')
    expect(wrapper.text()).toContain('收益类')
    expect(wrapper.text()).toContain('总盈亏')
    expect(wrapper.text()).toContain('累计收益率')
    expect(wrapper.text()).toContain('年化收益')
    expect(wrapper.text()).toContain('风险类')
    expect(wrapper.text()).toContain('最大回撤')
    expect(wrapper.text()).toContain('平均回撤')
    expect(wrapper.text()).toContain('比率类')
    expect(wrapper.text()).toContain('夏普比率')
    expect(wrapper.text()).toContain('索提诺')
    expect(wrapper.text()).toContain('卡玛比率')
  })

  it('should handle null values for unavailable metrics', async () => {
    const wrapper = mount(BacktestDetail, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': true,
          Line: { template: '<div class="chart-mock"></div>' },
          Bar: { template: '<div class="chart-mock"></div>' }
        }
      }
    })

    await wrapper.vm.$nextTick()

    const component = wrapper.vm as any

    expect(component.formatValue(null)).toBe('--')
    expect(component.formatValue(undefined)).toBe('--')
    expect(component.formatValue(125000)).toBe('125000.00')

    expect(component.formatPercent(null)).toBe('--')
    expect(component.formatPercent(undefined)).toBe('--')
    expect(component.formatPercent(0.155)).toBe('15.50%')
  })

  it('should not affect single backtest display', async () => {
    const wrapper = mount(BacktestDetail, {
      global: {
        plugins: [router],
        stubs: {
          'router-view': true,
          Line: { template: '<div class="chart-mock"></div>' },
          Bar: { template: '<div class="chart-mock"></div>' }
        }
      }
    })

    await wrapper.vm.$nextTick()

    const vm = wrapper.vm as any
    expect(vm.isBatch).toBe(false)

    vm.detail = mockSingleDetail
    await wrapper.vm.$nextTick()

    expect(vm.isBatch).toBe(false)
    expect(wrapper.text()).not.toContain('总股票数')
    expect(wrapper.text()).not.toContain('成功')
    expect(wrapper.text()).not.toContain('成功率')
    expect(wrapper.text()).toContain('总收益率')
    expect(wrapper.text()).toContain('年化收益率')
    expect(wrapper.text()).toContain('夏普比率')
    expect(wrapper.text()).toContain('最大回撤')
    expect(wrapper.text()).toContain('胜率')
    expect(wrapper.text()).toContain('交易次数')
  })
})
