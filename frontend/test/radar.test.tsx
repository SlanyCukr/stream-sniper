import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveSceneRadar: vi.fn(),
}))

vi.mock('@/lib/api/scene', () => api)

import {
  mapSceneRadar,
  useSceneRadar,
  type RadarChannel,
} from '@/hooks/scene/useSceneRadarQuery'
import RadarCard, { spikeBadge } from '@/components/scene/RadarCard'
import { computeBarHeights } from '@/components/scene/RadarSparkline'

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const minutes = (counts: number[]) => counts.map((messages, index) => ({
  minute: `2026-07-18T14:${String(index).padStart(2, '0')}:00`,
  messages,
}))

const spikingChannel = {
  stream_id: 1,
  creator_id: 10,
  creator_nick: 'hypecaster',
  creator_display_name: 'HypeCaster',
  profile_image_url: 'https://cdn.example/avatar.png',
  stream_title: 'CLUTCH OR KICK',
  started_at: '2026-07-18T13:00:00',
  messages_last_minute: 240,
  unique_chatters_last_minute: 88,
  baseline_per_minute: 80,
  ratio: 3,
  spiking: true,
  minutes: minutes([0, 5, 10]),
}

const quietChannel = {
  stream_id: 2,
  creator_id: 11,
  creator_nick: 'chillstreamer',
  creator_display_name: 'ChillStreamer',
  profile_image_url: null,
  stream_title: null,
  started_at: null,
  messages_last_minute: 12,
  unique_chatters_last_minute: 5,
  baseline_per_minute: null,
  ratio: null,
  spiking: false,
  minutes: minutes([0, 0, 0]),
}

describe('scene radar view-model contract', () => {
  beforeEach(() => vi.clearAllMocks())

  it('projects the wire payload into the camelCase view model, preserving nullable edges', () => {
    expect(mapSceneRadar({
      generated_at: '2026-07-18T14:03:00',
      channels: [spikingChannel, quietChannel],
    })).toEqual({
      generatedAt: '2026-07-18T14:03:00',
      channels: [
        {
          streamId: 1,
          creatorId: 10,
          creatorNick: 'hypecaster',
          creatorDisplayName: 'HypeCaster',
          profileImageUrl: 'https://cdn.example/avatar.png',
          streamTitle: 'CLUTCH OR KICK',
          startedAt: '2026-07-18T13:00:00',
          messagesLastMinute: 240,
          uniqueChattersLastMinute: 88,
          baselinePerMinute: 80,
          ratio: 3,
          spiking: true,
          minutes: minutes([0, 5, 10]),
        },
        {
          streamId: 2,
          creatorId: 11,
          creatorNick: 'chillstreamer',
          creatorDisplayName: 'ChillStreamer',
          profileImageUrl: null,
          streamTitle: null,
          startedAt: null,
          messagesLastMinute: 12,
          uniqueChattersLastMinute: 5,
          baselinePerMinute: null,
          ratio: null,
          spiking: false,
          minutes: minutes([0, 0, 0]),
        },
      ],
    })
  })

  it('accepts an all-quiet radar with no live channels', () => {
    expect(mapSceneRadar({ generated_at: '2026-07-18T14:03:00', channels: [] })).toEqual({
      generatedAt: '2026-07-18T14:03:00',
      channels: [],
    })
  })

  it.each([
    ['missing generated_at', { channels: [] }],
    ['missing channels', { generated_at: '2026-07-18T14:03:00' }],
    ['non-boolean spiking', { generated_at: 'x', channels: [{ ...spikingChannel, spiking: 'yes' }] }],
    ['minute missing messages', {
      generated_at: 'x',
      channels: [{ ...spikingChannel, minutes: [{ minute: '2026-07-18T14:00:00' }] }],
    }],
    ['null envelope', null],
  ])('rejects malformed radar payloads (%s)', (_label, payload) => {
    expect(() => mapSceneRadar(payload)).toThrow(TypeError)
  })

  it('fetches through the polling hook and maps the payload', async () => {
    api.retrieveSceneRadar.mockResolvedValue({
      generated_at: '2026-07-18T14:03:00', channels: [spikingChannel],
    })
    const { result } = renderHook(() => useSceneRadar(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.retrieveSceneRadar).toHaveBeenCalledTimes(1)
    expect(result.current.data?.channels[0]).toMatchObject({ streamId: 1, ratio: 3, spiking: true })
  })

  it('surfaces a malformed radar response as a boundary TypeError', async () => {
    api.retrieveSceneRadar.mockResolvedValue({})
    const { result } = renderHook(() => useSceneRadar(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeInstanceOf(TypeError)
  })

  it('does not fetch when disabled', async () => {
    renderHook(() => useSceneRadar({ enabled: false }), { wrapper: createWrapper() })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveSceneRadar).not.toHaveBeenCalled()
  })
})

describe('spike badge rule', () => {
  it('renders a red spiking chip carrying the ratio when known', () => {
    expect(spikeBadge(true, 3)).toEqual({ variant: 'err', label: 'SPIKING x3.0' })
  })

  it('keeps the spiking chip even when the ratio is unknown', () => {
    expect(spikeBadge(true, null)).toEqual({ variant: 'err', label: 'SPIKING' })
  })

  it('shows a neutral "vs usual" hint when not spiking but a ratio exists', () => {
    expect(spikeBadge(false, 1.4)).toEqual({ variant: 'neutral', label: 'x1.4 vs usual' })
  })

  it('shows nothing (never a misleading x0) when the ratio is null', () => {
    expect(spikeBadge(false, null)).toBeNull()
  })
})

describe('sparkline bar heights', () => {
  it('scales each minute relative to the busiest, zero staying zero', () => {
    expect(computeBarHeights(minutes([0, 5, 10]), 36)).toEqual([0, 18, 36])
  })

  it('collapses an all-quiet trace to all-zero bars (no divide-by-zero)', () => {
    expect(computeBarHeights(minutes([0, 0, 0]), 36)).toEqual([0, 0, 0])
  })

  it('clamps negative counts to a zero-height bar', () => {
    expect(computeBarHeights([{ messages: -4 }, { messages: 8 }], 36)).toEqual([0, 36])
  })
})

const asChannel = (raw: unknown): RadarChannel => mapSceneRadar({
  generated_at: 'x', channels: [raw],
}).channels[0]

describe('RadarCard rendering', () => {
  it('renders a spiking channel headline, badge, and creator link', () => {
    render(<RadarCard channel={asChannel(spikingChannel)} />)
    expect(screen.getByText('msgs/min')).toBeInTheDocument()
    expect(screen.getByText('SPIKING x3.0')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'HypeCaster' })).toHaveAttribute('href', '/creator/10')
    expect(screen.getByLabelText('Chat velocity, last 15 minutes')).toBeInTheDocument()
  })

  it('shows an em dash for a missing title and no badge when ratio is null', () => {
    render(<RadarCard channel={asChannel(quietChannel)} />)
    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.queryByText(/vs usual/)).not.toBeInTheDocument()
    expect(screen.queryByText(/SPIKING/)).not.toBeInTheDocument()
  })
})
