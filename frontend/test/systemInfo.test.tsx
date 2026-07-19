import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const hooks = vi.hoisted(() => ({
  useCacheStats: vi.fn(),
  useDetailedHealth: vi.fn(),
  useFlushCache: vi.fn(),
  useSystemMetrics: vi.fn(),
}))

vi.mock('@/hooks/admin/system/useSystemQueries', () => hooks)

import SystemInfo from '@/views/admin/SystemInfo'

describe('SystemInfo partial telemetry', () => {
  const flushCache = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    hooks.useFlushCache.mockReturnValue({ mutateAsync: flushCache })
  })

  it('shows a loading spinner before any telemetry has arrived', () => {
    const pendingQuery = {
      data: undefined,
      error: null,
      isPending: true,
      isFetching: true,
      refetch: vi.fn(),
    }
    hooks.useDetailedHealth.mockReturnValue(pendingQuery)
    hooks.useSystemMetrics.mockReturnValue(pendingQuery)
    hooks.useCacheStats.mockReturnValue(pendingQuery)

    render(<SystemInfo />)

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.getAllByText('Loading system telemetry...').length).toBeGreaterThan(0)
  })

  it('keeps successful panels visible while reporting and retrying a failed endpoint', () => {
    const refetchHealth = vi.fn()
    const refetchMetrics = vi.fn()
    const refetchCache = vi.fn()
    hooks.useDetailedHealth.mockReturnValue({
      data: {
        status: 'healthy',
        timestamp: '2026-07-14T10:00:00Z',
        uptimeSeconds: 90061,
        version: '1.2.3',
        memoryUsagePercent: 42.5,
        components: [],
      },
      error: null,
      isPending: false,
      isFetching: false,
      refetch: refetchHealth,
    })
    hooks.useSystemMetrics.mockReturnValue({
      data: undefined,
      error: { response: { status: 503 }, message: 'metrics offline' },
      isPending: false,
      isFetching: false,
      refetch: refetchMetrics,
    })
    hooks.useCacheStats.mockReturnValue({
      data: { backend: 'in-process', status: 'healthy', streamSniperKeys: 3 },
      error: null,
      isPending: false,
      isFetching: false,
      refetch: refetchCache,
    })

    render(<SystemInfo />)

    expect(screen.getByText('System telemetry incomplete')).toBeInTheDocument()
    expect(screen.getByText('System status').parentElement).toHaveTextContent('healthy')
    expect(screen.getByText('Cache').closest('.card')).toHaveTextContent('in-process')

    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(refetchHealth).toHaveBeenCalledOnce()
    expect(refetchMetrics).toHaveBeenCalledOnce()
    expect(refetchCache).toHaveBeenCalledOnce()
  })

  it('renders request telemetry and wires cache flush through the real statistics panel', async () => {
    flushCache.mockResolvedValue({ status: 'flushed' })
    hooks.useDetailedHealth.mockReturnValue({
      data: {
        status: 'degraded',
        timestamp: '2026-07-14T10:00:00Z',
        uptimeSeconds: 3660,
        version: '2.0.0',
        memoryUsagePercent: 55,
        components: [{ name: 'database', status: 'healthy', responseTimeMs: 2.5, details: 'ready' }],
      },
      error: null,
      isPending: false,
      isFetching: false,
      refetch: vi.fn(),
    })
    hooks.useSystemMetrics.mockReturnValue({
      data: {
        requests: {
          totalRequests: 100,
          successfulRequests: 90,
          failedRequests: 10,
          averageResponseTimeMs: 12.345,
        },
        cache: { hitRate: 0.75, totalHits: 75, totalMisses: 25, totalOperations: 100 },
        rateLimiting: null,
      },
      error: null,
      isPending: false,
      isFetching: false,
      refetch: vi.fn(),
    })
    hooks.useCacheStats.mockReturnValue({
      data: { backend: 'in-process', status: 'healthy', streamSniperKeys: 12 },
      error: null,
      isPending: false,
      isFetching: false,
      refetch: vi.fn(),
    })

    render(<SystemInfo />)

    expect(screen.getByText('Total requests').parentElement).toHaveTextContent('100')
    expect(screen.getByText('Hit rate').parentElement).toHaveTextContent('75.0%')
    expect(screen.getByRole('row', { name: /database healthy 2\.50ms ready/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Flush Cache' }))
    await waitFor(() => expect(flushCache).toHaveBeenCalledOnce())
    expect(await screen.findByText('Cache flushed successfully')).toBeInTheDocument()
  })
})
