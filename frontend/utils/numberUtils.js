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
