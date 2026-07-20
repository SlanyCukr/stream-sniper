import { parseNaiveUtcEpoch } from '@/utils/dateUtils'

const compactFormatter = new Intl.NumberFormat('en', {
    notation: 'compact',
    maximumFractionDigits: 1,
})

export const formatCompactNumber = (value: number | null | undefined): string => (
    compactFormatter.format(value || 0)
)

export const formatDurationHours = (seconds: number | null | undefined): string => (
    seconds == null ? '--' : `${Math.round(seconds / 3600).toLocaleString()}h`
)

export const formatDurationHoursMinutes = (seconds: number | null | undefined): string => {
    if (seconds == null) return '--'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
}

/**
 * Human duration "Xd Yh Zm" / "Xh Ym" / "Zm" from seconds, dropping leading
 * zero units. Distinct from formatDurationHoursMinutes: adds a days
 * component for long uptimes (e.g. system/process uptime).
 */
export const formatDurationDaysHoursMinutes = (seconds: number): string => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
}

/**
 * Locale-formatted integer (thousands separators, no decimals), or a
 * fallback when the value is null/undefined.
 *
 * Non-integer input is deliberately rounded to a whole number: this helper is
 * for count tiles (messages, chatters), where '1,234.5' would be wrong. (The
 * pre-consolidation streamMetricTiles `number()` left fractions visible; the
 * clamp here is the intended behavior, matching the report card's `integer()`.)
 */
export const formatInteger = (
    value: number | string | null | undefined,
    fallback = '--',
): string => (
    value == null ? fallback : Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })
)

/**
 * Locale-formatted number with exactly one decimal place, or a fallback
 * when the value is null/undefined.
 */
export const formatDecimal = (
    value: number | string | null | undefined,
    fallback = '--',
): string => (
    value == null ? fallback : Number(value).toLocaleString(undefined, {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
    })
)

/**
 * Clamp a magnitude bar to 2..100 for a value relative to the leading row in
 * its list (e.g. message counts among ranked chatters/creators/emotes).
 * Returns 0 (no bar) when top is non-positive — dividing by a non-positive
 * top has no meaningful magnitude to show.
 */
export const magnitudeBarWidth = (value: number, top: number): number => (
    top > 0 ? Math.min(100, Math.max(2, Math.round((value / top) * 100))) : 0
)

/**
 * Clamp a magnitude bar to 2..100 for a value already expressed as a 0..1
 * share (e.g. a chatter's fraction of a creator's messages). Unlike
 * magnitudeBarWidth, a zero share still renders a 2% sliver rather than an
 * empty bar: the domain here is a known ratio, not a value/top pair that is
 * undefined at zero.
 */
export const shareBarWidth = (share: number): number => (
    Math.min(100, Math.max(2, Math.round(share * 100)))
)

/**
 * Render a fractional share (0..1) as a single-decimal percentage string.
 * The one formatting rule for share/jaccard/hit-rate percentages app-wide.
 */
export const formatSharePct = (share: number): string => `${(share * 100).toFixed(1)}%`

/**
 * Human uptime "2h 14m" / "43m" from a live session start, or null when unknown
 * or the clock is skewed (negative elapsed). Shared by the live-now and radar cards.
 */
export const uptimeLabel = (startedAt: string | null): string | null => {
    const start = parseNaiveUtcEpoch(startedAt)
    if (start === null) return null
    const elapsedMs = Date.now() - start
    if (elapsedMs < 0) return null
    return formatDurationHoursMinutes(elapsedMs / 1000)
}
