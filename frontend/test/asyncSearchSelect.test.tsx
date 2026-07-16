import {
  act, fireEvent, render, screen, waitFor,
} from '@testing-library/react'
import {
  afterEach, describe, expect, it, vi,
} from 'vitest'

type MockSelectProps = { loadOptions: CallableFunction }
const selectHarness = vi.hoisted(() => ({
  loadOptions: null as CallableFunction | null,
  mode: null as 'async' | 'creatable' | null,
}))

vi.mock('react-select/async', () => ({
  default: ({ loadOptions }: MockSelectProps) => {
    selectHarness.loadOptions = loadOptions
    selectHarness.mode = 'async'
    return (
      <button type="button" onClick={() => void (loadOptions('operator') as Promise<unknown>).catch(() => {})}>
        search
      </button>
    )
  },
}))

vi.mock('react-select/async-creatable', () => ({
  default: ({ loadOptions }: MockSelectProps) => {
    selectHarness.loadOptions = loadOptions
    selectHarness.mode = 'creatable'
    return (
      <button type="button" onClick={() => void (loadOptions('operator') as Promise<unknown>).catch(() => {})}>
        search creatable
      </button>
    )
  },
}))

import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'

describe('AsyncSearchSelect', () => {
  afterEach(() => vi.useRealTimers())

  it('distinguishes a failed search and can retry the last query', async () => {
    const loadOptions = vi
      .fn()
      .mockRejectedValueOnce(new Error('search offline'))
      .mockResolvedValueOnce([{ value: 1, label: 'operator' }])

    render(<AsyncSearchSelect loadOptions={loadOptions} debounceMs={0} />)

    fireEvent.click(screen.getByRole('button', { name: 'search' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Search unavailable')

    fireEvent.click(screen.getByRole('button', { name: 'Retry search' }))
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
    expect(loadOptions).toHaveBeenNthCalledWith(1, 'operator')
    expect(loadOptions).toHaveBeenNthCalledWith(2, 'operator')
  })

  it('settles a superseded debounce before loading only the latest query', async () => {
    vi.useFakeTimers()
    const loadOptions = vi.fn().mockResolvedValue([{ value: 2, label: 'second' }])
    render(<AsyncSearchSelect loadOptions={loadOptions} debounceMs={50} />)

    const first = selectHarness.loadOptions?.('first') as Promise<unknown>
    const second = selectHarness.loadOptions?.('second') as Promise<unknown>

    await expect(first).resolves.toEqual([])
    await act(async () => vi.runAllTimersAsync())
    await expect(second).resolves.toEqual([{ value: 2, label: 'second' }])
    expect(loadOptions).toHaveBeenCalledOnce()
    expect(loadOptions).toHaveBeenCalledWith('second')
  })

  it('settles a pending debounce on unmount without starting a search', async () => {
    vi.useFakeTimers()
    const loadOptions = vi.fn().mockResolvedValue([])
    const { unmount } = render(<AsyncSearchSelect loadOptions={loadOptions} debounceMs={50} />)

    const pending = selectHarness.loadOptions?.('pending') as Promise<unknown>
    unmount()

    await expect(pending).resolves.toEqual([])
    await act(async () => vi.runAllTimersAsync())
    expect(loadOptions).not.toHaveBeenCalled()
  })

  it('preserves and reports a repeated retry failure', async () => {
    const onLoadError = vi.fn()
    const loadOptions = vi
      .fn()
      .mockRejectedValueOnce(new Error('search offline'))
      .mockRejectedValueOnce(new Error('still offline'))

    render(
      <AsyncSearchSelect
        loadOptions={loadOptions}
        debounceMs={0}
        onLoadError={onLoadError}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: 'search' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry search' }))

    await waitFor(() => expect(loadOptions).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry search' })).toBeEnabled())
    expect(screen.getByRole('alert')).toHaveTextContent('Search unavailable')
    expect(onLoadError).toHaveBeenCalledTimes(2)
  })

  it('retains creatable selection mode while delegating loading', async () => {
    const loadOptions = vi.fn().mockResolvedValue([{ value: 3, label: 'created' }])
    render(<AsyncSearchSelect creatable loadOptions={loadOptions} debounceMs={0} />)

    expect(selectHarness.mode).toBe('creatable')
    fireEvent.click(screen.getByRole('button', { name: 'search creatable' }))
    await waitFor(() => expect(loadOptions).toHaveBeenCalledWith('operator'))
  })
})
