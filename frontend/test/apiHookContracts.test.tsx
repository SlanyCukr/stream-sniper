import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveCommunityOverlap: vi.fn(),
  retrieveCreatorNeighbors: vi.fn(),
  retrieveCacheStats: vi.fn(),
  retrieveDetailedHealth: vi.fn(),
  retrieveMetrics: vi.fn(),
  retrieveStreams: vi.fn(),
  retrieveStreamComprehensive: vi.fn(),
}))

vi.mock('@/lib/api/community', () => ({
  retrieveCommunityOverlap: api.retrieveCommunityOverlap,
  retrieveCreatorNeighbors: api.retrieveCreatorNeighbors,
}))

vi.mock('@/lib/api/system', () => ({
  retrieveCacheStats: api.retrieveCacheStats,
  retrieveDetailedHealth: api.retrieveDetailedHealth,
  retrieveMetrics: api.retrieveMetrics,
}))

vi.mock('@/lib/api/streams', () => ({
  retrieveStreams: api.retrieveStreams,
  retrieveStreamComprehensive: api.retrieveStreamComprehensive,
}))

import { useCacheStats, useDetailedHealth, useSystemMetrics } from '@/hooks/admin/system/useSystemQueries'
import { useCommunityOverlap, useCreatorNeighbors } from '@/hooks/community/useCommunityQuery'
import { useStreamDetails, useStreams } from '@/hooks/stream/list/useStreamsQuery'

const createWrapper = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('API hook contract boundaries', () => {
  beforeEach(() => vi.clearAllMocks())

  it.each([
    ['stream list', () => {
      api.retrieveStreams.mockResolvedValue({})
      return renderHook(() => useStreams(), { wrapper: createWrapper() })
    }],
    ['stream detail', () => {
      api.retrieveStreamComprehensive.mockResolvedValue({})
      return renderHook(() => useStreamDetails(7), { wrapper: createWrapper() })
    }],
    ['community overlap', () => {
      api.retrieveCommunityOverlap.mockResolvedValue({})
      return renderHook(() => useCommunityOverlap(), { wrapper: createWrapper() })
    }],
    ['creator neighbors', () => {
      api.retrieveCreatorNeighbors.mockResolvedValue({})
      return renderHook(() => useCreatorNeighbors(7), { wrapper: createWrapper() })
    }],
    ['detailed health', () => {
      api.retrieveDetailedHealth.mockResolvedValue({})
      return renderHook(() => useDetailedHealth(), { wrapper: createWrapper() })
    }],
    ['system metrics', () => {
      api.retrieveMetrics.mockResolvedValue({})
      return renderHook(() => useSystemMetrics(), { wrapper: createWrapper() })
    }],
    ['cache stats', () => {
      api.retrieveCacheStats.mockResolvedValue({})
      return renderHook(() => useCacheStats(), { wrapper: createWrapper() })
    }],
  ])('rejects a malformed %s payload instead of returning empty success', async (_name, render) => {
    const hook = render()
    await waitFor(() => expect((hook.result.current as any).isError).toBe(true))
    expect((hook.result.current as any).error).toBeInstanceOf(TypeError)
  })

  it('keeps hook-owned query functions and keys authoritative', async () => {
    api.retrieveDetailedHealth.mockResolvedValue({
      status: 'healthy',
      timestamp: 'now',
      uptime_seconds: 12,
      system: { memory_usage_percent: 5 },
      components: {},
    })
    const foreignQuery = vi.fn(async () => ({ status: 'foreign' }))
    const hook = renderHook(
      () => useDetailedHealth({ queryKey: ['foreign'], queryFn: foreignQuery }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))
    expect(api.retrieveDetailedHealth).toHaveBeenCalledOnce()
    expect(foreignQuery).not.toHaveBeenCalled()
    expect(hook.result.current.data?.status).toBe('healthy')
  })

  it('does not let callers enable a query whose required resource ID is absent', async () => {
    const hook = renderHook(() => useStreamDetails(0, { enabled: true }), { wrapper: createWrapper() })
    await waitFor(() => expect((hook.result.current as any).fetchStatus).toBe('idle'))
    expect(api.retrieveStreamComprehensive).not.toHaveBeenCalled()
  })

  it('honors an explicit disabled option for queries without a required resource ID', async () => {
    const hook = renderHook(() => useStreams({}, { enabled: false }), { wrapper: createWrapper() })
    await waitFor(() => expect((hook.result.current as any).fetchStatus).toBe('idle'))
    expect(api.retrieveStreams).not.toHaveBeenCalled()
  })
})
