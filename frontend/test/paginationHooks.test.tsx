import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { UseQueryResult } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveChatterMessages: vi.fn(),
  retrieveStreamComprehensive: vi.fn(),
  retrieveStreams: vi.fn(),
}))

vi.mock('@/lib/api/chatter', () => ({
  retrieveChatterMessages: api.retrieveChatterMessages,
}))
vi.mock('@/lib/api/streams', () => ({
  retrieveStreamComprehensive: api.retrieveStreamComprehensive,
  retrieveStreams: api.retrieveStreams,
}))

import { useMessages } from '@/hooks/chatter/useMessagesQuery'
import { useStreams } from '@/hooks/stream/list/useStreamsQuery'

type Page<T> = {
  items: T[]
  total: number
  pageIndex: number
  pageSize: number
  pageCount: number
}

type StreamListItem = {
  streamId: number
  creatorName: string
  start: string
  end: string | null
  thumbnailUrl: string | null
  messageCount: number
}

type ChatterMessage = {
  streamId: number
  streamTitle: string
  creatorDisplayName: string
  text: string
  timestamp: string
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('paginated hook boundaries', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.retrieveStreams.mockResolvedValue({
      data: {
        streams: [{
          stream_id: 1,
          creator_name: 'Operator',
          start: '2026-07-14T10:00:00Z',
          end: null,
          thumbnail_url: null,
          message_count: 42,
        }],
        total: 41,
        offset: 40,
        limit: 20,
      },
    })
    api.retrieveChatterMessages.mockResolvedValue({
      data: { messages: [{
        stream_id: 1,
        stream_title: 'Stream',
        creator_display_name: 'Creator',
        text: 'message',
        timestamp: '2026-01-01T00:00:00',
      }], total: 101, offset: 100, limit: 50 },
    })
  })

  it('maps a stream page index to the endpoint row offset and returns page metadata', async () => {
    const { result } = renderHook(() => useStreams({ pageIndex: 2 }) as UseQueryResult<Page<StreamListItem>>, {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.retrieveStreams).toHaveBeenCalledWith(expect.objectContaining({ rowOffset: 40 }))
    expect(result.current.data).toEqual({
      items: [{
        streamId: 1,
        creatorName: 'Operator',
        start: '2026-07-14T10:00:00Z',
        end: null,
        thumbnailUrl: null,
        messageCount: 42,
      }],
      total: 41,
      pageIndex: 2,
      pageSize: 20,
      pageCount: 3,
    })
  })

  it('maps configurable message pages at the endpoint boundary', async () => {
    const { result } = renderHook(
      () => useMessages(7, { pageIndex: 2, pageSize: 50 }) as UseQueryResult<Page<ChatterMessage>>,
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.retrieveChatterMessages).toHaveBeenCalledWith(7, {
      rowOffset: 100,
      pageSize: 50,
    })
    expect(result.current.data).toEqual({
      items: [{
        streamId: 1,
        streamTitle: 'Stream',
        creatorDisplayName: 'Creator',
        text: 'message',
        timestamp: '2026-01-01T00:00:00',
      }],
      total: 101,
      pageIndex: 2,
      pageSize: 50,
      pageCount: 3,
    })
  })
})
