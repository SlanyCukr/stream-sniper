import { describe, expect, it } from 'vitest'
import {
  formatCompactNumber,
  formatDurationHours,
  formatDurationHoursMinutes,
  formatDurationDaysHoursMinutes,
  formatInteger,
  formatDecimal,
} from '@/utils/numberUtils'

describe('formatCompactNumber', () => {
  it('formats large numbers compactly', () => {
    expect(formatCompactNumber(12345)).toBe('12.3K')
  })

  it('treats a falsy value as 0', () => {
    expect(formatCompactNumber(null)).toBe('0')
  })
})

describe('formatDurationHours', () => {
  it('rounds seconds to whole hours', () => {
    expect(formatDurationHours(7200)).toBe('2h')
  })

  it('returns -- for null', () => {
    expect(formatDurationHours(null)).toBe('--')
  })
})

describe('formatDurationHoursMinutes', () => {
  it('formats hours and minutes', () => {
    expect(formatDurationHoursMinutes(8100)).toBe('2h 15m')
  })

  it('omits hours when zero', () => {
    expect(formatDurationHoursMinutes(120)).toBe('2m')
  })

  it('returns -- for null', () => {
    expect(formatDurationHoursMinutes(null)).toBe('--')
  })
})

describe('formatDurationDaysHoursMinutes', () => {
  it('formats days, hours, and minutes', () => {
    expect(formatDurationDaysHoursMinutes(86400 * 2 + 3600 * 3 + 60 * 5)).toBe('2d 3h 5m')
  })

  it('omits days when zero', () => {
    expect(formatDurationDaysHoursMinutes(3600 * 3 + 60 * 5)).toBe('3h 5m')
  })

  it('omits days and hours when both zero', () => {
    expect(formatDurationDaysHoursMinutes(60 * 5)).toBe('5m')
  })
})

describe('formatInteger', () => {
  it('formats with thousands separators', () => {
    expect(formatInteger(12345)).toBe('12,345')
  })

  it('returns -- for null/undefined by default', () => {
    expect(formatInteger(null)).toBe('--')
    expect(formatInteger(undefined)).toBe('--')
  })

  it('accepts a custom fallback', () => {
    expect(formatInteger(null, 'n/a')).toBe('n/a')
  })
})

describe('formatDecimal', () => {
  it('formats with exactly one decimal place', () => {
    expect(formatDecimal(1.23)).toBe('1.2')
    expect(formatDecimal(1)).toBe('1.0')
  })

  it('returns -- for null/undefined by default', () => {
    expect(formatDecimal(null)).toBe('--')
  })

  it('accepts a custom fallback', () => {
    expect(formatDecimal(undefined, 'n/a')).toBe('n/a')
  })
})
