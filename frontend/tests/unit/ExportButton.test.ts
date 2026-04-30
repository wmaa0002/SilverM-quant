import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ExportButton from '@/components/ExportButton.vue'

describe('ExportButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
  })

  describe('Component Rendering', () => {
    it('renders export button', () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      expect(wrapper.find('button').text()).toContain('导出')
    })

    it('renders with correct runId', () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      expect(wrapper.props('runId')).toBe('test-123')
    })

    it('button is enabled when disabled prop is false', () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123', disabled: false }
      })
      
      expect(wrapper.find('button').attributes('disabled')).toBeUndefined()
    })

    it('button is disabled when disabled prop is true', () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123', disabled: true }
      })
      
      expect(wrapper.find('button').attributes('disabled')).toBeDefined()
    })
  })

  describe('User Interactions', () => {
    it('opens dropdown on click', async () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      const dropdown = wrapper.find('.absolute.right-0')
      expect(dropdown.isVisible()).toBe(true)
    })

    it('closes dropdown when clicking backdrop', async () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      await wrapper.find('.fixed.inset-0').trigger('click')
      await flushPromises()
      
      expect(wrapper.find('.absolute.right-0').exists()).toBe(false)
    })

    it('does not open dropdown when disabled', async () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123', disabled: true }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      expect(wrapper.find('.absolute.right-0').exists()).toBe(false)
    })

    it('shows CSV option in dropdown', async () => {
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      expect(wrapper.text()).toContain('CSV')
      expect(wrapper.text()).toContain('JSON')
    })
  })

  describe('Export Functionality', () => {
    it('shows loading state during export', async () => {
      const mockFetch = vi.fn().mockImplementation(() => {
        return new Promise(() => {})
      })
      global.fetch = mockFetch
      
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      await wrapper.findAll('button')[1].trigger('click')
      await flushPromises()
      
      expect(wrapper.find('button').text()).toContain('导出中')
    })

    it('calls exportData with csv format', async () => {
      const mockResponse = new Response(new Blob(['test'], { type: 'text/csv' }), {
        status: 200,
        headers: { 'Content-Disposition': 'filename=test.csv' }
      })
      const mockFetch = vi.fn().mockResolvedValue(mockResponse)
      global.fetch = mockFetch
      
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      await wrapper.findAll('button')[1].trigger('click')
      await flushPromises()
      
      expect(mockFetch).toHaveBeenCalledWith('/api/backtest/test-123/export?format=csv')
    })

    it('calls exportData with json format', async () => {
      const mockResponse = new Response(new Blob(['{}'], { type: 'application/json' }), {
        status: 200,
        headers: { 'Content-Disposition': 'filename=test.json' }
      })
      const mockFetch = vi.fn().mockResolvedValue(mockResponse)
      global.fetch = mockFetch
      
      const wrapper = mount(ExportButton, {
        props: { runId: 'test-123' }
      })
      
      await wrapper.find('button').trigger('click')
      await flushPromises()
      
      await wrapper.findAll('button')[2].trigger('click')
      await flushPromises()
      
      expect(mockFetch).toHaveBeenCalledWith('/api/backtest/test-123/export?format=json')
    })
  })
})