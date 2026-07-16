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
