import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveChattersOnStream: vi.fn(),
  retrieveChatterIdentity: vi.fn(),
  retrieveChatterStreamActivity: vi.fn(),
}))

vi.mock('@/lib/api/chatter', () => api)

import ChatterFootprintPanel from '@/components/chatter/ChatterFootprintPanel'
import {
  chattersKeys,
  useChatterIdentity,
  useChatters,
  useChatterStreamActivity,
} from '@/hooks/chatter/useChattersQuery'

const createClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('chatter query contracts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('maps stream chatter rows through the authoritative key and adapter', async () => {
    api.retrieveChattersOnStream.mockResolvedValue({ data: [{ chatter_id: 7, nick: 'alice' }] })
    const queryClient = createClient()
    const hook = renderHook(() => useChatters(42), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))

    expect(api.retrieveChattersOnStream).toHaveBeenCalledWith(42)
    expect(hook.result.current.data).toEqual([{ chatterId: 7, nick: 'alice' }])
    expect(queryClient.getQueryData(chattersKeys.list(42))).toEqual([
      { chatterId: 7, nick: 'alice' },
    ])
  })

  it.each([
    [{}, 'stream chatters must be an array'],
    [[{ chatter_id: 7 }], 'stream chatters[0].nick must be a string'],
  ])('rejects malformed stream chatter payloads', async (data, message) => {
    api.retrieveChattersOnStream.mockResolvedValue({ data })
    const hook = renderHook(() => useChatters(42), {
      wrapper: createWrapper(createClient()),
    })

    await waitFor(() => expect(hook.result.current.isError).toBe(true))
    expect(hook.result.current.error).toEqual(expect.objectContaining({ message }))
  })

  it('maps a named chatter identity response', async () => {
    const expected = { chatterId: 7, isBot: true }
    api.retrieveChatterIdentity.mockResolvedValue({ data: { chatter_id: 7, is_bot: true } })
    const queryClient = createClient()
    const hook = renderHook(() => useChatterIdentity('alice', { enabled: true }), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))
    expect(api.retrieveChatterIdentity).toHaveBeenCalledWith('alice')
    expect(hook.result.current.data).toEqual(expected)
    expect(queryClient.getQueryData(chattersKeys.chatterId('alice'))).toEqual(expected)
  })

  it.each([[7, true], 9, null])('rejects a legacy chatter identity response', async data => {
    api.retrieveChatterIdentity.mockResolvedValue({ data })
    const hook = renderHook(() => useChatterIdentity('alice', { enabled: true }), {
      wrapper: createWrapper(createClient()),
    })

    await waitFor(() => expect(hook.result.current.isError).toBe(true))
    expect(hook.result.current.error).toEqual(expect.objectContaining({
      message: 'chatter identity must be an object',
    }))
  })

  it('does not call adapters without required IDs or explicit chatter-ID enablement', async () => {
    const wrapper = createWrapper(createClient())
    renderHook(() => useChatters(0), { wrapper })
    renderHook(() => useChatterStreamActivity(0), { wrapper })
    renderHook(() => useChatterIdentity('alice'), { wrapper })
    renderHook(() => useChatterIdentity('', { enabled: true }), { wrapper })

    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveChattersOnStream).not.toHaveBeenCalled()
    expect(api.retrieveChatterStreamActivity).not.toHaveBeenCalled()
    expect(api.retrieveChatterIdentity).not.toHaveBeenCalled()
  })

  it('rejects malformed activity payloads', async () => {
    api.retrieveChatterStreamActivity.mockResolvedValue({ data: {} })
    const hook = renderHook(() => useChatterStreamActivity(7), {
      wrapper: createWrapper(createClient()),
    })

    await waitFor(() => expect(hook.result.current.isError).toBe(true))
    expect(hook.result.current.error).toEqual(expect.objectContaining({
      message: 'chatter stream activity must be an array',
    }))
  })

  it('feeds the real activity hook into the chatter footprint panel', async () => {
    const activity = [
      {
        stream_id: 10,
        stream_title: 'Launch stream',
        start: '2026-01-01T12:00:00',
        creator_id: 3,
        creator_display_name: 'creator',
        message_count: 42,
        is_bot: null,
      },
    ]
    api.retrieveChatterStreamActivity.mockResolvedValue({ data: activity })
    const queryClient = createClient()

    render(
      <QueryClientProvider client={queryClient}>
        <ChatterFootprintPanel chatter={{ value: 7, label: 'alice' }} />
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('link', { name: 'Launch stream' })).toHaveAttribute(
      'href',
      '/stream/10',
    )
    expect(api.retrieveChatterStreamActivity).toHaveBeenCalledWith(7)
    expect(queryClient.getQueryData(chattersKeys.streamActivity(7))).toEqual([{
      streamId: 10,
      streamTitle: 'Launch stream',
      start: '2026-01-01T12:00:00',
      creatorId: 3,
      creatorDisplayName: 'creator',
      messageCount: 42,
      isBot: null,
    }])
  })
})
