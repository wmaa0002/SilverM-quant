import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import StrategySelector from '@/components/StrategySelector.vue'

const defaultStrategies = [
  { id: 'B1', name: 'B1策略', description: 'B1买入策略' },
  { id: 'B2', name: 'B2策略', description: 'B2买入策略' },
  { id: 'BLK', name: 'BLK策略', description: '暴力K策略', defaultThreshold: 5 }
]

describe('StrategySelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('renders with empty selection', () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      expect(wrapper.find('button').text()).toContain('选择策略')
    })

    it('renders with selected strategies count', () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: ['B1', 'B2'],
          availableStrategies: defaultStrategies
        }
      })
      
      expect(wrapper.find('button').text()).toContain('已选择 2 个策略')
    })

    it('renders all available strategies in dropdown', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const checkboxes = wrapper.findAll('input[type="checkbox"]')
      expect(checkboxes.length).toBe(3)
    })

    it('shows selected strategy tags', () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: ['B1'],
          availableStrategies: defaultStrategies
        }
      })
      
      const tags = wrapper.findAll('.bg-blue-500\\/20 span:first-child')
      expect(tags.length).toBe(1)
      expect(tags[0].text()).toContain('B1策略')
    })
  })

  describe('User Interactions', () => {
    it('opens dropdown on button click', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      expect(wrapper.find('.absolute.z-50').isVisible()).toBe(true)
    })

    it('closes dropdown when clicking backdrop', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      await wrapper.find('.fixed.inset-0').trigger('click')
      await flushPromises()
      
      expect(wrapper.find('.absolute.z-50').exists()).toBe(false)
    })

    it('toggles strategy selection on checkbox click', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const checkbox = wrapper.find('input[type="checkbox"]')
      await checkbox.trigger('change')
      await flushPromises()
      
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    })

    it('selects all strategies when clicking select all', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const buttons = wrapper.findAll('.absolute.z-50 button')
      const selectAllBtn = buttons.find(btn => btn.text() === '全选')
      expect(selectAllBtn).toBeDefined()
      await selectAllBtn!.trigger('click')
      await flushPromises()
      
      expect(wrapper.emitted('update:modelValue')?.[0]).toBeTruthy()
    })

    it('deselects all strategies when clicking deselect all', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: ['B1', 'B2'],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const buttons = wrapper.findAll('.absolute.z-50 button')
      const deselectAllBtn = buttons.find(btn => btn.text() === '清空')
      expect(deselectAllBtn).toBeDefined()
      await deselectAllBtn!.trigger('click')
      await flushPromises()
      
      const emitted = wrapper.emitted('update:modelValue')
      expect(emitted?.[0]?.[0]).toEqual([])
    })

    it('removes strategy tag when clicking X on tag', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: ['B1'],
          availableStrategies: defaultStrategies
        }
      })
      
      const removeBtn = wrapper.find('.rounded-full button')
      await removeBtn.trigger('click')
      await flushPromises()
      
      expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual([])
    })
  })

  describe('Threshold Parameter', () => {
    it('displays threshold input for strategies', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const thresholdInputs = wrapper.findAll('input[type="number"]')
      expect(thresholdInputs.length).toBe(3)
    })

    it('uses default threshold value', async () => {
      const wrapper = mount(StrategySelector, {
        props: {
          modelValue: [],
          availableStrategies: defaultStrategies
        }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const blkkInput = wrapper.findAll('input[type="number"]')[2]
      expect((blkkInput.element as HTMLInputElement).value).toBe('5')
    })
  })
})