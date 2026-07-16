import { describe, expect, it, vi } from 'vitest'

import { loadUntilTimestamp } from '@/hooks/stream/replay/useStreamReplayController'

const replayData = (...timestamps: string[]) => ({
  pages: timestamps.map(ts => ({ messages: [{ ts }] })),
})

describe('bounded replay target loading', () => {
  it('finds a target already present without fetching', async () => {
    const fetchNextPage = vi.fn()

    const outcome = await loadUntilTimestamp({
      initialData: replayData('2026-07-15T08:05:00Z'),
      targetTs: '2026-07-15T08:04:00Z',
      hasNextPage: true,
      fetchNextPage,
    })

    expect(outcome).toMatchObject({ status: 'found', pagesFetched: 0 })
    expect(fetchNextPage).not.toHaveBeenCalled()
  })

  it('reports an unavailable target when history is exhausted', async () => {
    const outcome = await loadUntilTimestamp({
      initialData: replayData('2026-07-15T08:00:00Z'),
      targetTs: '2026-07-15T08:04:00Z',
      hasNextPage: false,
      fetchNextPage: vi.fn(),
    })

    expect(outcome).toMatchObject({ status: 'unavailable', pagesFetched: 0 })
  })

  it('stops at the page budget and can continue from the returned data', async () => {
    const firstFetch = vi.fn()
      .mockResolvedValueOnce({
        data: replayData('2026-07-15T08:00:00Z', '2026-07-15T08:01:00Z'),
        hasNextPage: true,
      })
      .mockResolvedValueOnce({
        data: replayData(
          '2026-07-15T08:00:00Z',
          '2026-07-15T08:01:00Z',
          '2026-07-15T08:02:00Z',
        ),
        hasNextPage: true,
      })

    const exhausted = await loadUntilTimestamp({
      initialData: replayData('2026-07-15T08:00:00Z'),
      targetTs: '2026-07-15T08:04:00Z',
      hasNextPage: true,
      fetchNextPage: firstFetch,
      maxPages: 2,
    })

    expect(exhausted).toMatchObject({ status: 'exhausted', pagesFetched: 2 })

    const continued = await loadUntilTimestamp({
      initialData: exhausted.data,
      targetTs: '2026-07-15T08:04:00Z',
      hasNextPage: true,
      fetchNextPage: vi.fn().mockResolvedValue({
        data: replayData(
          '2026-07-15T08:00:00Z',
          '2026-07-15T08:01:00Z',
          '2026-07-15T08:02:00Z',
          '2026-07-15T08:05:00Z',
        ),
        hasNextPage: false,
      }),
      maxPages: 2,
    })

    expect(continued).toMatchObject({ status: 'found', pagesFetched: 1 })
  })

  it('stops when the elapsed-time budget is reached', async () => {
    const now = vi.fn()
      .mockReturnValueOnce(0)
      .mockReturnValueOnce(0)
      .mockReturnValueOnce(6)
    const fetchNextPage = vi.fn().mockResolvedValue({
      data: replayData('2026-07-15T08:01:00Z'),
      hasNextPage: true,
    })

    const outcome = await loadUntilTimestamp({
      initialData: replayData('2026-07-15T08:00:00Z'),
      targetTs: '2026-07-15T08:04:00Z',
      hasNextPage: true,
      fetchNextPage,
      maxPages: 10,
      maxElapsedMs: 5,
      now,
    })

    expect(outcome).toMatchObject({ status: 'exhausted', pagesFetched: 1 })
    expect(fetchNextPage).toHaveBeenCalledOnce()
  })
})
