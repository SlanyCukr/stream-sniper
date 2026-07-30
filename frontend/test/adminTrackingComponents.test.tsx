import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const trackingHooks = vi.hoisted(() => ({ loadTrackedStreamerOptions: vi.fn() }))
let searchProps: {
  loadOptions: CallableFunction
  onChange: CallableFunction
} | null = null

vi.mock('@/hooks/admin/tracking/useTrackingQueries', () => trackingHooks)
vi.mock('@/components/common/search/AsyncSearchSelect', () => ({
  default: (props: typeof searchProps) => {
    searchProps = props
    return <button type="button" onClick={() => props?.onChange({ value: 'operator' })}>Choose operator</button>
  },
}))

import AddTrackedStreamerModal from '@/components/admin/tracking/streamers/AddTrackedStreamerModal'
import ProcessingJobsStatistics from '@/components/admin/tracking/jobs/ProcessingJobsStatistics'

describe('ProcessingJobsStatistics', () => {
  it('renders a processing slice with null-safe zero values in either presentation', () => {
    const { rerender } = render(
      <ProcessingJobsStatistics processingStats={{ total: 4, pending: null }} />,
    )
    expect(screen.getByText('Processing jobs')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getAllByText('0')).toHaveLength(5)

    rerender(
      <ProcessingJobsStatistics processingStats={{ total: 2 }} card={false} heading="" />,
    )
    expect(screen.queryByText('Processing jobs')).not.toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })
})

describe('AddTrackedStreamerModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    searchProps = null
  })

  it('owns search, draft, submit, and reset behavior', async () => {
    const onCreate = vi.fn().mockResolvedValue({ ok: true })
    const onHide = vi.fn()
    trackingHooks.loadTrackedStreamerOptions.mockImplementation(async (query: string) => (
      query.trim().length < 2 ? [] : [{ value: 'operator', label: 'Operator (operator)' }]
    ))
    render(<AddTrackedStreamerModal show onHide={onHide} onCreate={onCreate} />)

    await expect(searchProps!.loadOptions('o')).resolves.toEqual([])
    expect(trackingHooks.loadTrackedStreamerOptions).toHaveBeenCalledWith('o')
    await expect(searchProps!.loadOptions('op')).resolves.toEqual([
      { value: 'operator', label: 'Operator (operator)' },
    ])

    fireEvent.click(screen.getByRole('button', { name: 'Choose operator' }))
    fireEvent.change(screen.getByPlaceholderText('Optional notes about this streamer'), {
      target: { value: 'priority' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add Streamer' }))

    await waitFor(() => expect(onCreate).toHaveBeenCalledWith({
      twitchUsername: 'operator',
      notes: 'priority',
      isActive: true,
      processingEnabled: true,
    }))
    expect(onHide).toHaveBeenCalledOnce()
  })

  it('propagates channel-search failures and leaves failed creates open', async () => {
    const onCreate = vi.fn().mockResolvedValue({ ok: false })
    const onHide = vi.fn()
    trackingHooks.loadTrackedStreamerOptions.mockRejectedValue(new Error('search failed'))
    render(<AddTrackedStreamerModal show onHide={onHide} onCreate={onCreate} />)

    await expect(searchProps!.loadOptions('op')).rejects.toThrow('search failed')
    act(() => searchProps!.onChange({ value: 'operator' }))
    fireEvent.click(screen.getByRole('button', { name: 'Add Streamer' }))

    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce())
    expect(onHide).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Add Streamer' })).toBeEnabled()
  })

  it('blocks every dismissal control while creation is pending', () => {
    const onHide = vi.fn()
    const { rerender } = render(
      <AddTrackedStreamerModal
        show
        pending
        onHide={onHide}
        onCreate={vi.fn()}
      />,
    )

    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onHide).not.toHaveBeenCalled()

    rerender(
      <AddTrackedStreamerModal
        show
        pending={false}
        onHide={onHide}
        onCreate={vi.fn()}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onHide).toHaveBeenCalledOnce()
  })

  it('keeps the modal locked until its create promise settles', async () => {
    let finishCreate: (outcome: { ok: boolean }) => void = () => undefined
    const onCreate = vi.fn(() => new Promise<{ ok: boolean }>((resolve) => {
      finishCreate = resolve
    }))
    const onHide = vi.fn()
    render(<AddTrackedStreamerModal show onHide={onHide} onCreate={onCreate} />)
    act(() => searchProps!.onChange({ value: 'operator' }))

    fireEvent.click(screen.getByRole('button', { name: 'Add Streamer' }))
    expect(await screen.findByRole('button', { name: 'Adding...' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Close' })).not.toBeInTheDocument()
    expect(onHide).not.toHaveBeenCalled()

    finishCreate({ ok: true })
    await waitFor(() => expect(onHide).toHaveBeenCalledOnce())
  })
})
