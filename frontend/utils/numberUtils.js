const compactFormatter = new Intl.NumberFormat('en', {
    notation: 'compact',
    maximumFractionDigits: 1,
})

export const formatCompactNumber = value => compactFormatter.format(value || 0)

export const formatDurationHours = seconds => (
    seconds == null ? '--' : `${Math.round(seconds / 3600).toLocaleString()}h`
)

export const formatDurationHoursMinutes = seconds => {
    if (seconds == null) return '--'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
}

/**
 * Human duration "Xd Yh Zm" / "Xh Ym" / "Zm" from seconds, dropping leading
 * zero units. Distinct from formatDurationHoursMinutes: adds a days
 * component for long uptimes (e.g. system/process uptime).
 * @param {number} seconds
 */
export const formatDurationDaysHoursMinutes = seconds => {
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
 * @param {number|string|null|undefined} value
 * @param {string} [fallback]
 */
export const formatInteger = (value, fallback = '--') => (
    value == null ? fallback : Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })
)

/**
 * Locale-formatted number with exactly one decimal place, or a fallback
 * when the value is null/undefined.
 * @param {number|string|null|undefined} value
 * @param {string} [fallback]
 */
export const formatDecimal = (value, fallback = '--') => (
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
 * @param {number} value
 * @param {number} top
 */
export const magnitudeBarWidth = (value, top) => (
    top > 0 ? Math.min(100, Math.max(2, Math.round((value / top) * 100))) : 0
)

/**
 * Clamp a magnitude bar to 2..100 for a value already expressed as a 0..1
 * share (e.g. a chatter's fraction of a creator's messages). Unlike
 * magnitudeBarWidth, a zero share still renders a 2% sliver rather than an
 * empty bar: the domain here is a known ratio, not a value/top pair that is
 * undefined at zero.
 * @param {number} share
 */
export const shareBarWidth = share => (
    Math.min(100, Math.max(2, Math.round(share * 100)))
)
