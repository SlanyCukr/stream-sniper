import { beforeEach, describe, expect, it, vi } from 'vitest'

const client = vi.hoisted(() => ({
  api: {
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  getJson: vi.fn(),
}))

vi.mock('@/lib/api/client', () => client)

import { createTrackedStreamer, updateTrackedStreamer } from '@/lib/api/tracking'

describe('tracking mutation transport', () => {
  beforeEach(() => vi.clearAllMocks())

  it('serializes create commands at the API adapter boundary', () => {
    createTrackedStreamer({
      twitchUsername: 'operator',
      notes: 'priority',
      isActive: true,
      processingEnabled: false,
    })

    expect(client.api.post).toHaveBeenCalledWith('/admin/tracking/streamers', {
      twitch_username: 'operator',
      notes: 'priority',
      is_active: true,
      processing_enabled: false,
    })
  })

  it('serializes partial update commands at the API adapter boundary', () => {
    updateTrackedStreamer(7, { isActive: false, notes: null })

    expect(client.api.put).toHaveBeenCalledWith('/admin/tracking/streamers/7', {
      is_active: false,
      processing_enabled: undefined,
      notes: null,
    })
  })
})
