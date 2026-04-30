import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import axios from 'axios'
import { useBacktestStore } from '@/stores/backtestStore'

vi.mock('axios')

describe('backtestStore', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  describe('State Initialization', () => {
    it('initializes with empty strategies', () => {
      const store = useBacktestStore()
      
      expect(store.strategies).toEqual([])
    })

    it('initializes with empty selected strategies', () => {
      const store = useBacktestStore()
      
      expect(store.selectedStrategies).toEqual([])
    })

    it('initializes with empty date range', () => {
      const store = useBacktestStore()
      
      expect(store.startDate).toBe('')
      expect(store.endDate).toBe('')
    })

    it('initializes with default stock selection mode as all', () => {
      const store = useBacktestStore()
      
      expect(store.stockSelectionMode).toBe('all')
    })

    it('initializes with default initial capital of 1000000', () => {
      const store = useBacktestStore()
      
      expect(store.initialCapital).toBe(1000000)
    })

    it('initializes with isLoading as false', () => {
      const store = useBacktestStore()
      
      expect(store.isLoading).toBe(false)
    })

    it('initializes with null current result', () => {
      const store = useBacktestStore()
      
      expect(store.currentResult).toBeNull()
    })

    it('initializes with null error', () => {
      const store = useBacktestStore()
      
      expect(store.error).toBeNull()
    })
  })

  describe('Getters', () => {
    it('hasResult returns false when currentResult is null', () => {
      const store = useBacktestStore()
      
      expect(store.hasResult).toBe(false)
    })

    it('hasResult returns true when currentResult status is completed', () => {
      const store = useBacktestStore()
      store.currentResult = { run_id: 'test', status: 'completed' }
      
      expect(store.hasResult).toBe(true)
    })

    it('hasResult returns false when currentResult status is running', () => {
      const store = useBacktestStore()
      store.currentResult = { run_id: 'test', status: 'running' }
      
      expect(store.hasResult).toBe(false)
    })

    it('isRunning returns isLoading value', () => {
      const store = useBacktestStore()
      store.isLoading = true
      
      expect(store.isRunning).toBe(true)
    })
  })

  describe('Actions', () => {
    describe('fetchStrategies', () => {
      it('sets strategies on successful fetch', async () => {
        const mockStrategies = [
          { name: 'B1', description: 'B1策略' },
          { name: 'B2', description: 'B2策略' }
        ]
        
        ;(vi.mocked(axios.get) as ReturnType<typeof vi.fn>).mockResolvedValue({
          data: { strategies: mockStrategies }
        })
        
        const store = useBacktestStore()
        await store.fetchStrategies()
        
        expect(store.strategies).toEqual(mockStrategies)
      })

      it('sets error on fetch failure', async () => {
        ;(vi.mocked(axios.get) as ReturnType<typeof vi.fn>).mockRejectedValue(
          new Error('Network error')
        )
        
        const store = useBacktestStore()
        await store.fetchStrategies()
        
        expect(store.error).toBe('获取策略列表失败')
      })

      it('sets isLoading during fetch', async () => {
        ;(vi.mocked(axios.get) as ReturnType<typeof vi.fn>).mockImplementation(
          () => new Promise(resolve => setTimeout(resolve, 10))
        )
        
        const store = useBacktestStore()
        const fetchPromise = store.fetchStrategies()
        expect(store.isLoading).toBe(true)
        await fetchPromise
        expect(store.isLoading).toBe(false)
      })
    })

    describe('setDateRange', () => {
      it('sets start and end date', () => {
        const store = useBacktestStore()
        store.setDateRange('2024-01-01', '2024-12-31')
        
        expect(store.startDate).toBe('2024-01-01')
        expect(store.endDate).toBe('2024-12-31')
      })
    })

    describe('setSelectedStrategies', () => {
      it('sets selected strategies', () => {
        const store = useBacktestStore()
        store.setSelectedStrategies(['B1', 'B2'])
        
        expect(store.selectedStrategies).toEqual(['B1', 'B2'])
      })
    })

    describe('setStockSelection', () => {
      it('sets stock selection mode and stocks', () => {
        const store = useBacktestStore()
        store.setStockSelection('single', ['600000'])
        
        expect(store.stockSelectionMode).toBe('single')
        expect(store.selectedStocks).toEqual(['600000'])
      })

      it('clears stocks when mode is all', () => {
        const store = useBacktestStore()
        store.selectedStocks = ['600000']
        store.setStockSelection('all')
        
        expect(store.selectedStocks).toEqual([])
      })
    })

    describe('resetResult', () => {
      it('clears current result and error', () => {
        const store = useBacktestStore()
        store.currentResult = { run_id: 'test', status: 'completed' }
        store.error = 'some error'
        
        store.resetResult()
        
        expect(store.currentResult).toBeNull()
        expect(store.error).toBeNull()
      })
    })

    describe('runBacktest validation', () => {
      it('sets error if no strategies selected', async () => {
        const store = useBacktestStore()
        store.selectedStrategies = []
        
        await store.runBacktest()
        
        expect(store.error).toBe('请至少选择一个策略')
      })

      it('sets error if no date range selected', async () => {
        const store = useBacktestStore()
        store.selectedStrategies = ['B1']
        store.startDate = ''
        store.endDate = ''
        
        await store.runBacktest()
        
        expect(store.error).toBe('请选择日期范围')
      })
    })
  })
})