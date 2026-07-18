import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const hooks = vi.hoisted(() => ({
  loadTrackedStreamerOptions: vi.fn(),
  useCreateTrackedStreamer: vi.fn(),
  useDeleteTrackedStreamer: vi.fn(),
  useTrackedStreamers: vi.fn(),
  useUpdateTrackedStreamer: vi.fn(),
}))

vi.mock('@/hooks/admin/tracking/useTrackingQueries', () => hooks)
vi.mock('@/lib/api/tracking', () => ({ retrieveTwitchChannelSearch: vi.fn() }))
vi.mock('@/components/common/search/AsyncSearchSelect', () => ({
  default: () => <div data-testid="streamer-search" />,
}))

import StreamerTracking from '@/views/admin/StreamerTracking'

const streamer = {
  id: 7,
  twitchUsername: 'operator',
  displayName: 'Operator',
  isActive: true,
  processingEnabled: true,
  lastStreamCheck: null,
  createdAt: '2026-07-14T10:00:00Z',
}

describe('StreamerTracking pagination', () => {
  const deleteStreamer = { mutateAsync: vi.fn(), isPending: false }
  const updateStreamer = { mutateAsync: vi.fn(), isPending: false }

  beforeEach(() => {
    vi.clearAllMocks()
    deleteStreamer.mutateAsync.mockResolvedValue(undefined)
    updateStreamer.mutateAsync.mockResolvedValue(undefined)
    hooks.useCreateTrackedStreamer.mockReturnValue({ mutateAsync: vi.fn() })
    hooks.loadTrackedStreamerOptions.mockResolvedValue([])
    hooks.useDeleteTrackedStreamer.mockReturnValue(deleteStreamer)
    hooks.useUpdateTrackedStreamer.mockReturnValue(updateStreamer)
  })

  it('moves to the previous page after deleting its last row', async () => {
    const queryParams: Array<Record<string, unknown>> = []
    hooks.useTrackedStreamers.mockImplementation((params) => {
      queryParams.push(params)
      return {
        data: {
          items: [streamer],
          total: 21,
          pageIndex: params.pageIndex,
          pageSize: 20,
          pageCount: 2,
        },
        error: null,
        isPending: false,
      }
    })

    render(<StreamerTracking />)
    fireEvent.click(screen.getByLabelText('Go to page 2'))
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 1 })

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    const removeButtons = await screen.findAllByRole('button', { name: 'Remove' })
    fireEvent.click(removeButtons.at(-1)!)

    await waitFor(() => expect(deleteStreamer.mutateAsync).toHaveBeenCalledWith(7))
    await waitFor(() => expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0 }))
  })

  it('emits normalized filters and row update commands', async () => {
    const queryParams: Array<Record<string, unknown>> = []
    hooks.useTrackedStreamers.mockImplementation((params) => {
      queryParams.push(params)
      return {
        data: { items: [streamer], total: 1, pageIndex: 0, pageSize: 20, pageCount: 1 },
        error: null,
        isPending: false,
      }
    })

    render(<StreamerTracking />)
    fireEvent.change(screen.getByLabelText('Filter by status'), { target: { value: 'false' } })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, isActive: false })

    fireEvent.click(screen.getByRole('button', { name: 'Deactivate' }))
    await waitFor(() => expect(updateStreamer.mutateAsync).toHaveBeenCalledWith({
      streamerId: 7,
      changes: { is_active: false },
    }))

    fireEvent.click(screen.getByRole('button', { name: 'Disable' }))
    await waitFor(() => expect(updateStreamer.mutateAsync).toHaveBeenCalledWith({
      streamerId: 7,
      changes: { processing_enabled: false },
    }))
  })

  it('normalizes mutation failures at the tracking boundary', async () => {
    updateStreamer.mutateAsync.mockRejectedValue({ response: { status: 500, data: { detail: 'update offline' } } })
    hooks.useTrackedStreamers.mockReturnValue({
      data: { items: [streamer], total: 1, pageIndex: 0, pageSize: 20, pageCount: 1 },
      error: null,
      isPending: false,
    })

    render(<StreamerTracking />)
    fireEvent.click(screen.getByRole('button', { name: 'Deactivate' }))
    await waitFor(() => expect(screen.getByText('update offline')).toBeInTheDocument())
  })
})
