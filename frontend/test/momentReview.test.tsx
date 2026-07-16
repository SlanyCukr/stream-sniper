import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { deleteMomentReview, putMomentReview, retrieveMomentsQueue } = vi.hoisted(() => ({
  deleteMomentReview: vi.fn(),
  putMomentReview: vi.fn(),
  retrieveMomentsQueue: vi.fn(),
}))

vi.mock('@/lib/api/moments', () => ({
  deleteMomentReview,
  putMomentReview,
  retrieveMomentsQueue,
}))

import { momentsQueueKeys, useMomentReview, useMomentsQueue } from '@/hooks/moments/useMomentsQueries'
import { streamTimelineKeys } from '@/hooks/queryKeys'
import MomentReviewControls from '@/components/moments/MomentReviewControls'

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('useMomentReview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    putMomentReview.mockResolvedValue({ data: { status: 'clipped' } })
    deleteMomentReview.mockResolvedValue({ data: undefined })
  })

  it('decodes the complete queue envelope and uses server pagination metadata', async () => {
    retrieveMomentsQueue.mockResolvedValue({ data: {
      items: [],
      total: 81,
      limit: 20,
      offset: 40,
    } })
    const { result } = renderHook(() => useMomentsQueue({ pageIndex: 2, pageSize: 20 }), {
      wrapper: createWrapper(new QueryClient({ defaultOptions: { queries: { retry: false } } })),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toEqual({
      items: [],
      total: 81,
      pageIndex: 2,
      pageSize: 20,
      pageCount: 5,
    })
  })

  it('sets a review, awaits owned invalidation, then calls the consumer callback', async () => {
    const queryClient = new QueryClient()
    const events: string[] = []
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(async (filters) => {
      events.push(`invalidate:${JSON.stringify(filters?.queryKey)}`)
    })
    const onSuccess = vi.fn(async () => {
      events.push('consumer-success')
    })
    const { result } = renderHook(() => useMomentReview({ onSuccess }), {
      wrapper: createWrapper(queryClient),
    })

    await act(async () => {
      await result.current.mutateAsync({
        action: 'set',
        streamId: 42,
        bucketMinute: '2026-07-14T10:30:00',
        status: 'clipped',
        clipUrl: null,
        note: null,
      })
    })

    expect(putMomentReview).toHaveBeenCalledWith(
      42,
      '2026-07-14T10:30:00',
      'clipped',
      { clipUrl: null, note: null },
    )
    expect(deleteMomentReview).not.toHaveBeenCalled()
    expect(invalidate).toHaveBeenCalledWith({ queryKey: momentsQueueKeys.all })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: streamTimelineKeys.detail(42) })
    expect(events.at(-1)).toBe('consumer-success')
  })

  it('uses an explicit clear command for deletion', async () => {
    const queryClient = new QueryClient()
    vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue()
    const { result } = renderHook(() => useMomentReview(), {
      wrapper: createWrapper(queryClient),
    })

    await act(async () => {
      await result.current.mutateAsync({
        action: 'clear',
        streamId: 42,
        bucketMinute: '2026-07-14T10:30:00',
      })
    })

    expect(deleteMomentReview).toHaveBeenCalledWith(42, '2026-07-14T10:30:00')
    expect(putMomentReview).not.toHaveBeenCalled()
  })

  it('keeps clip editing open until the review command succeeds', async () => {
    const onReview = vi.fn().mockRejectedValueOnce(new Error('save failed'))
    render(<MomentReviewControls
      isAdmin
      pending={false}
      status="bookmarked"
      clipUrl={null}
      note={null}
      vodHref={null}
      onReview={onReview}
    />)

    fireEvent.click(screen.getByRole('button', { name: 'Attach clip' }))
    fireEvent.change(screen.getByLabelText('Clip URL'), {
      target: { value: 'https://clips.twitch.tv/example' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save clip' }))
    await waitFor(() => expect(onReview).toHaveBeenCalledOnce())
    expect(screen.getByLabelText('Clip URL')).toBeInTheDocument()

    onReview.mockResolvedValueOnce({ status: 'clipped' })
    fireEvent.click(screen.getByRole('button', { name: 'Save clip' }))
    await waitFor(() => expect(screen.queryByLabelText('Clip URL')).not.toBeInTheDocument())
  })
})
