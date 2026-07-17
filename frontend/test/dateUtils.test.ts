import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  formatDurationBetween,
  formatDateTime,
  formatDurationSeconds,
  parseNaiveUtcEpoch,
  formatClockTime,
} from '@/utils/dateUtils'

describe('formatDurationBetween', () => {
  afterEach(() => vi.useRealTimers())

  it('treats a null end date as the current time for live streams', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-07-14T11:30:00Z'))

    expect(formatDurationBetween('2026-07-14T10:00:00Z', null)).toBe('1h 30m')
  })
})

describe('formatDateTime', () => {
  it('formats a date via the runtime locale', () => {
    const date = new Date('2026-07-14T10:00:00Z')
    expect(formatDateTime(date)).toBe(date.toLocaleString())
  })

  it('falls back to N/A for a falsy input by default', () => {
    expect(formatDateTime(null)).toBe('N/A')
    expect(formatDateTime(undefined)).toBe('N/A')
    expect(formatDateTime('')).toBe('N/A')
  })

  it('accepts a custom fallback', () => {
    expect(formatDateTime(null, 'Never')).toBe('Never')
  })
})

describe('formatDurationSeconds', () => {
  it('returns whole seconds between two dates', () => {
    expect(formatDurationSeconds('2026-07-14T10:00:00Z', '2026-07-14T10:00:45Z')).toBe('45s')
  })

  it('falls back when either date is missing', () => {
    expect(formatDurationSeconds(null, '2026-07-14T10:00:45Z')).toBe('N/A')
    expect(formatDurationSeconds('2026-07-14T10:00:00Z', null)).toBe('N/A')
  })

  it('accepts a custom fallback', () => {
    expect(formatDurationSeconds(null, null, 'Pending')).toBe('Pending')
  })
})

describe('parseNaiveUtcEpoch', () => {
  it('parses a naive UTC timestamp (no zone suffix) as UTC', () => {
    expect(parseNaiveUtcEpoch('2026-07-14T10:00:00')).toBe(new Date('2026-07-14T10:00:00Z').getTime())
  })

  it('returns null for non-string or too-short input', () => {
    expect(parseNaiveUtcEpoch(null)).toBeNull()
    expect(parseNaiveUtcEpoch('2026-07-14')).toBeNull()
  })
})

describe('formatClockTime', () => {
  it('slices HH:MM from an ISO-ish timestamp', () => {
    expect(formatClockTime('2026-07-14T10:05:00')).toBe('10:05')
  })

  it('returns -- for a too-short or non-string input', () => {
    expect(formatClockTime('short')).toBe('--')
    expect(formatClockTime(null)).toBe('--')
  })
})
