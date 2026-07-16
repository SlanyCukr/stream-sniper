import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { router } from './mocks/navigation'

const hooks = vi.hoisted(() => ({
  useCreators: vi.fn(),
  useStreams: vi.fn(),
}))

vi.mock('@/hooks/creator/useCreatorsQuery', () => ({
  useCreators: hooks.useCreators,
  mapCreatorOption: (creator: { creatorId: number; nick: string }) => ({
    value: creator.creatorId,
    label: creator.nick,
  }),
}))
vi.mock('@/hooks/stream/list/useStreamsQuery', async (importOriginal) => ({
  ...await importOriginal<typeof import('@/hooks/stream/list/useStreamsQuery')>(),
  useStreams: hooks.useStreams,
}))
vi.mock('@/hooks/useDebouncedValue', () => ({ useDebouncedValue: (value: string) => value }))
vi.mock('react-select', () => ({
  default: ({
    'aria-label': ariaLabel,
    onChange,
    options,
    value,
  }: {
    'aria-label': string
    onChange: CallableFunction
    options: Array<{ label: string; value: string | number }>
    value: { value: string | number } | null
  }) => (
    <select
      aria-label={ariaLabel}
      value={value?.value ?? ''}
      onChange={(event) => onChange(
        options.find((option) => String(option.value) === event.target.value) ?? null,
      )}
    >
      <option value="">All</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  ),
}))

import AllStreams from '@/views/stream/AllStreams'
import { mapStreamInfo } from '@/hooks/stream/list/useStreamsQuery'

describe('AllStreams filter controller', () => {
  const queryParams: Array<Record<string, unknown>> = []

  beforeEach(() => {
    vi.clearAllMocks()
    queryParams.length = 0
    hooks.useCreators.mockReturnValue({
      data: [{ creatorId: 7, nick: 'Operator' }],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    hooks.useStreams.mockImplementation((params) => {
      queryParams.push(params)
      return {
        data: {
          items: [{
            streamId: 1,
            creatorName: 'Operator',
            start: '2026-07-14T10:00:00Z',
            end: null,
            thumbnailUrl: null,
            messageCount: 42,
          }],
          total: 41,
          pageIndex: params.pageIndex,
          pageSize: 20,
          pageCount: 3,
        },
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      }
    })
  })

  const moveToSecondPage = () => {
    fireEvent.click(screen.getByLabelText('Go to page 2'))
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 1 })
  }

  it('returns every stream filter command to the first page', () => {
    render(<AllStreams />)

    moveToSecondPage()
    fireEvent.change(screen.getByLabelText('Search stream titles'), { target: { value: 'needle' } })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, title: 'needle' })

    moveToSecondPage()
    fireEvent.change(screen.getByLabelText('Filter streams by creator'), { target: { value: '7' } })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, creatorId: 7 })

    moveToSecondPage()
    fireEvent.change(screen.getByLabelText('Sort streams by different criteria'), { target: { value: 'message_count' } })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, sort: 'message_count' })

    moveToSecondPage()
    fireEvent.click(screen.getByRole('button', { name: /sort direction descending/i }))
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, dir: 'asc' })

    moveToSecondPage()
    fireEvent.change(screen.getByLabelText('From date'), { target: { value: '2026-07-01' } })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, dateFrom: '2026-07-01' })

    moveToSecondPage()
    fireEvent.change(screen.getByLabelText('To date'), { target: { value: '2026-07-31' } })
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, dateTo: '2026-07-31' })

    moveToSecondPage()
    const minimumMessages = screen.getByLabelText('Minimum messages')
    fireEvent.change(minimumMessages, { target: { value: '50' } })
    fireEvent.blur(minimumMessages)
    expect(queryParams.at(-1)).toMatchObject({ pageIndex: 0, minMessages: 50 })

    moveToSecondPage()
    fireEvent.change(minimumMessages, { target: { value: '75' } })
    fireEvent.keyDown(minimumMessages, { key: 'Enter' })
    expect(queryParams.filter(params => params.minMessages === 75)).toHaveLength(1)

    moveToSecondPage()
    fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(queryParams.at(-1)).toMatchObject({
      pageIndex: 0,
      creatorId: -1,
      dir: 'desc',
      title: undefined,
      dateFrom: undefined,
      dateTo: undefined,
      minMessages: undefined,
    })
    expect(minimumMessages).toHaveValue(null)
  })

  it('renders the real stream card and navigates through its public control', () => {
    render(<AllStreams />)
    fireEvent.click(screen.getByRole('button', {
      name: "View details for Operator's stream with 42 messages",
    }))
    expect(router.push).toHaveBeenCalledWith('/stream/1')
    expect(screen.getByText('LIVE')).toBeInTheDocument()
  })
})

describe('mapStreamInfo', () => {
  it('maps each named comprehensive-stream field', () => {
    expect(mapStreamInfo({
      title: 'A stream', start: 'start', end: 'end', thumbnail_url: 'thumb', message_count: 42,
      creator_nick: 'nick', creator_display_name: 'Display', profile_image_url: 'profile', creator_id: 7,
    })).toEqual({
      title: 'A stream',
      start: 'start',
      end: 'end',
      thumbnailUrl: 'thumb',
      messageCount: 42,
      nick: 'nick',
      displayName: 'Display',
      profileImageUrl: 'profile',
      creatorId: 7,
    })
  })
})
