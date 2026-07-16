import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const hooks = vi.hoisted(() => ({
  useProcessingJobs: vi.fn(),
  useTrackedStreamerOptions: vi.fn(),
  useTrackingStats: vi.fn(),
}))

vi.mock('@/hooks/admin/tracking/useTrackingQueries', () => hooks)
vi.mock('react-select', () => ({
  default: ({ isDisabled }: { isDisabled?: boolean }) => (
    <label>
      Streamer filter
      <select aria-label="Streamer filter" disabled={isDisabled} />
    </label>
  ),
}))

import ProcessingJobs from '@/views/admin/ProcessingJobs'

const jobData = {
  items: [{
    id: 91,
    twitchUsername: 'operator',
    streamerDisplayName: null,
    twitchVodId: 'stream-1',
    status: 'completed',
    createdAt: '2026-07-14T10:00:00Z',
    startedAt: '2026-07-14T10:01:00Z',
    completedAt: '2026-07-14T10:02:00Z',
    retryCount: 0,
  }],
  total: 1,
  pageIndex: 0,
  pageSize: 50,
  pageCount: 1,
}

describe('ProcessingJobs auxiliary query failures', () => {
  beforeEach(() => {
    hooks.useProcessingJobs.mockReturnValue({
      data: jobData,
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })
  })

  it('shows a statistics failure without hiding available jobs', async () => {
    const refetchStats = vi.fn()
    hooks.useTrackingStats.mockReturnValue({
      data: undefined,
      error: { response: { status: 503 }, message: 'stats offline' },
      isPending: false,
      refetch: refetchStats,
    })
    hooks.useTrackedStreamerOptions.mockReturnValue({
      data: [],
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })

    render(<ProcessingJobs />)

    expect(screen.getByText('operator')).toBeInTheDocument()
    expect(screen.getByText('Processing statistics unavailable')).toBeInTheDocument()
    expect(screen.queryByText('Total')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(refetchStats).toHaveBeenCalledOnce()
  })

  it('shows a streamer-option failure, disables that filter, and keeps statistics and jobs', () => {
    hooks.useTrackingStats.mockReturnValue({
      data: { processingJobs: { total: 1, completed: 1 } },
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })
    hooks.useTrackedStreamerOptions.mockReturnValue({
      data: undefined,
      error: { response: { status: 503 }, message: 'options offline' },
      isPending: false,
      refetch: vi.fn(),
    })

    render(<ProcessingJobs />)

    expect(screen.getByText('operator')).toBeInTheDocument()
    expect(screen.getByText('Streamer filters unavailable')).toBeInTheDocument()
    expect(screen.getByText('Total')).toBeInTheDocument()
    expect(screen.getByLabelText('Streamer filter')).toBeDisabled()
  })

  it('returns to the first page when a filter changes', () => {
    const queryParams: Array<Record<string, unknown>> = []
    hooks.useProcessingJobs.mockImplementation((params) => {
      queryParams.push(params)
      return {
        data: { ...jobData, total: 101, pageCount: 3 },
        error: null,
        isPending: false,
        refetch: vi.fn(),
      }
    })
    hooks.useTrackingStats.mockReturnValue({
      data: { processingJobs: { total: 101 } },
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })
    hooks.useTrackedStreamerOptions.mockReturnValue({
      data: [],
      error: null,
      isPending: false,
      refetch: vi.fn(),
    })

    render(<ProcessingJobs />)
    fireEvent.click(screen.getByLabelText('Go to page 2'))
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 1, pageSize: 50 })

    fireEvent.change(screen.getByLabelText('Filter by status'), {
      target: { value: 'failed' },
    })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, status: 'failed' })
  })
})
