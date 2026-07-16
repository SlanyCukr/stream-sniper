import { useCallback, useMemo } from 'react'

export const TIMELINE_WIDTH = 1000
export const MESSAGE_HEIGHT = 160
export const VIEWER_HEIGHT = 72

export const buildViewerLane = (buckets, viewerSamples) => {
    const count = buckets.length
    if (viewerSamples.length === 0 || count === 0) return null
    const first = Date.parse(buckets[0].t)
    const last = Date.parse(buckets[count - 1].t)
    const span = last - first
    const points = viewerSamples
        .map(sample => {
            const at = Date.parse(sample.t)
            const raw = span > 0 && Number.isFinite(at)
                ? ((at - first) / span) * (count - 1)
                : 0
            const idxFrac = Math.min(count - 1, Math.max(0, raw))
            return {
                idxFrac,
                viewers: sample.viewerCount || 0,
                x: ((idxFrac + 0.5) / count) * TIMELINE_WIDTH,
            }
        })
        .sort((left, right) => left.x - right.x)
    const maxViewers = Math.max(1, ...points.map(point => point.viewers))
    const y = viewers => VIEWER_HEIGHT - (viewers / maxViewers) * VIEWER_HEIGHT
    const line = points
        .map(point => `${point.x.toFixed(2)},${y(point.viewers).toFixed(2)}`)
        .join(' ')
    const area = points.length
        ? `M ${points[0].x.toFixed(2)},${VIEWER_HEIGHT} `
            + points.map(point => `L ${point.x.toFixed(2)},${y(point.viewers).toFixed(2)}`).join(' ')
            + ` L ${points[points.length - 1].x.toFixed(2)},${VIEWER_HEIGHT} Z`
        : ''
    return { points, maxViewers, line, area }
}

export const getMarkerLeft = (buckets, timestamp) => {
    const count = buckets.length
    if (count === 0) return 0
    const exactIndex = buckets.findIndex(bucket => bucket.t === timestamp)
    if (exactIndex >= 0) return ((exactIndex + 0.5) / count) * 100
    const first = Date.parse(buckets[0].t)
    const last = Date.parse(buckets[count - 1].t)
    const at = Date.parse(timestamp)
    if (!Number.isFinite(at) || last <= first) return 0
    return Math.min(100, Math.max(0, ((at - first) / (last - first)) * 100))
}

export const getHoverIndex = (clientX, left, width, bucketCount) => {
    if (bucketCount === 0 || width <= 0) return null
    const fraction = (clientX - left) / width
    return Math.min(bucketCount - 1, Math.max(0, Math.floor(fraction * bucketCount)))
}

export const getNearestViewerCount = (viewerLane, hoverIndex) => {
    if (!viewerLane || hoverIndex == null) return null
    let nearest = null
    let distance = Infinity
    for (const point of viewerLane.points) {
        const candidateDistance = Math.abs(point.idxFrac - hoverIndex)
        if (candidateDistance < distance) {
            distance = candidateDistance
            nearest = point.viewers
        }
    }
    return nearest
}

export const useTimelineGeometry = (buckets, viewerSamples, hoverIndex) => {
    const bucketCount = buckets.length
    const maxCount = useMemo(
        () => Math.max(1, ...buckets.map(bucket => bucket.count || 0)),
        [buckets],
    )
    const viewerLane = useMemo(
        () => buildViewerLane(buckets, viewerSamples),
        [buckets, viewerSamples],
    )
    const markerLeft = useCallback(
        timestamp => getMarkerLeft(buckets, timestamp),
        [buckets],
    )
    const hovered = hoverIndex == null ? null : buckets[hoverIndex]
    const barSlot = bucketCount ? TIMELINE_WIDTH / bucketCount : 0
    const barWidth = Math.max(1, barSlot * 0.72)
    return {
        bucketCount,
        maxCount,
        viewerLane,
        markerLeft,
        hovered,
        hoveredHeight: hovered ? ((hovered.count || 0) / maxCount) * MESSAGE_HEIGHT : 0,
        hoveredViewers: getNearestViewerCount(viewerLane, hoverIndex),
        barSlot,
        barWidth,
        crosshairLeft: hovered
            ? `calc(2.6rem + ${((hoverIndex + 0.5) / bucketCount)} * (100% - 2.6rem))`
            : null,
    }
}
