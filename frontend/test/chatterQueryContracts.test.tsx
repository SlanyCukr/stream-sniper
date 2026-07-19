import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveChatterStreamActivity: vi.fn(),
}))

vi.mock('@/lib/api/chatter', () => api)

import ChatterFootprintPanel from '@/components/chatter/ChatterFootprintPanel'
import {
  chattersKeys,
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

  it('does not call the activity adapter without a chatter ID', async () => {
    const wrapper = createWrapper(createClient())
    renderHook(() => useChatterStreamActivity(0), { wrapper })

    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveChatterStreamActivity).not.toHaveBeenCalled()
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
