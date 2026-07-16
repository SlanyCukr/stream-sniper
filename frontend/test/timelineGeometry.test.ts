import { describe, expect, it } from 'vitest'
import {
  buildViewerLane,
  getHoverIndex,
  getMarkerLeft,
  getNearestViewerCount,
} from '@/hooks/stream/timeline/useTimelineGeometry'

const buckets = [
  { t: '2026-07-14T10:00:00Z' },
  { t: '2026-07-14T10:01:00Z' },
  { t: '2026-07-14T10:02:00Z' },
]

describe('timeline geometry', () => {
  it('maps exact and fractional timestamps into bounded marker positions', () => {
    expect(getMarkerLeft(buckets, buckets[1].t)).toBe(50)
    expect(getMarkerLeft(buckets, '2026-07-14T10:00:30Z')).toBe(25)
    expect(getMarkerLeft(buckets, 'invalid')).toBe(0)
  })

  it('maps pointer positions to bounded bucket indexes', () => {
    expect(getHoverIndex(125, 100, 100, 4)).toBe(1)
    expect(getHoverIndex(500, 100, 100, 4)).toBe(3)
    expect(getHoverIndex(100, 100, 0, 4)).toBeNull()
  })

  it('builds aligned viewer paths and finds the nearest sample', () => {
    const lane = buildViewerLane(buckets, [
      { t: buckets[0].t, viewerCount: 10 },
      { t: buckets[2].t, viewerCount: 30 },
    ])
    expect(lane?.line).toContain('166.67,48.00')
    expect(lane?.maxViewers).toBe(30)
    expect(getNearestViewerCount(lane, 2)).toBe(30)
  })
})
