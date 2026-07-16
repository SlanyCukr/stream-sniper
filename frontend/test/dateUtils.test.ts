import { afterEach, describe, expect, it, vi } from 'vitest'
import { formatDurationBetween } from '@/utils/dateUtils'

describe('formatDurationBetween', () => {
  afterEach(() => vi.useRealTimers())

  it('treats a null end date as the current time for live streams', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-14T11:30:00Z'))

    expect(formatDurationBetween('2026-07-14T10:00:00Z', null)).toBe('1h 30m')
  })
})
