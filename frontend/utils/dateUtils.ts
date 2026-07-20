import {
    format, formatDistanceToNow, intervalToDuration, type Duration,
} from 'date-fns'

const DATE_FORMATS = {
    LONG: 'MMMM dd, yyyy HH:mm:ss',
    STREAM_TIMESTAMP: 'yyyy/MM/dd HH:mm:ss',
}

type DateInput = Date | string | number

const parseDate = (dateInput: DateInput): Date => {
    if (dateInput instanceof Date) return dateInput
    if (typeof dateInput === 'string' || typeof dateInput === 'number') {
        return new Date(dateInput)
    }
    throw new TypeError('Invalid date input')
}

const validDateOrNull = (value: DateInput): Date | null => {
    try {
        const date = parseDate(value)
        return Number.isNaN(date.getTime()) ? null : date
    } catch {
        return null
    }
}

export const formatDate = (date: DateInput, formatPattern: string = DATE_FORMATS.LONG): string => {
    const parsed = validDateOrNull(date)
    return parsed ? format(parsed, formatPattern) : 'Invalid date'
}

/** Short date via formatDate, or an em dash for a missing (null/undefined) value. */
export const formatDateOrDash = (
    date: DateInput | null | undefined,
    formatPattern = 'MMM d, yyyy',
): string => (date ? formatDate(date, formatPattern) : '—')

export const formatTimeAgo = (
    date: DateInput,
    options: Parameters<typeof formatDistanceToNow>[1] = {},
): string => {
    const parsed = validDateOrNull(date)
    if (!parsed) return 'Invalid date'
    return formatDistanceToNow(parsed, {
        addSuffix: true,
        ...options,
    }).replace(/^(about|over|almost|less than) /, '')
}

const buildDurationParts = ({
    years = 0, months = 0, days = 0, hours = 0, minutes = 0, seconds = 0,
}: Duration): string[] => {
    const parts = []
    if (years > 0) parts.push(`${years}y`)
    if (months > 0) parts.push(`${months}mo`)
    if (days > 0) parts.push(`${days}d`)
    if (hours > 0) parts.push(`${hours}h`)
    if (minutes > 0) parts.push(`${minutes}m`)
    if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`)
    return parts
}

/** @param endDate null means still live */
export const formatDurationBetween = (startDate: DateInput, endDate: DateInput | null): string => {
    const start = validDateOrNull(startDate)
    const end = endDate == null ? new Date() : validDateOrNull(endDate)
    if (!start || !end || end < start) return 'Invalid duration'
    return buildDurationParts(intervalToDuration({ start, end })).join(' ')
}

/**
 * Locale-formatted date+time via `Date#toLocaleString`, or a fallback when
 * the input is falsy. Distinct from formatDate (fixed date-fns pattern):
 * this defers to the browser/runtime locale, matching admin table cells
 * that previously called `toLocaleString()` directly.
 *
 * Strict on input types: truthy values that are not a Date/string/number throw
 * (via parseDate) rather than being coerced the way a bare `new Date(x)` would —
 * a deliberate tightening so shape bugs surface instead of rendering garbage.
 */
export const formatDateTime = (
    date: DateInput | null | undefined,
    fallback = 'N/A',
): string => (
    date ? parseDate(date).toLocaleString() : fallback
)

/**
 * Whole-second duration "Ns" between two dates, or a fallback when either
 * is missing. Distinct from formatDurationBetween: no unit breakdown, just
 * whole seconds — used for short-lived processing-job durations.
 */
export const formatDurationSeconds = (
    startDate: DateInput | null | undefined,
    endDate: DateInput | null | undefined,
    fallback = 'N/A',
): string => {
    if (!startDate || !endDate) return fallback
    const seconds = Math.floor(
        (parseDate(endDate).getTime() - parseDate(startDate).getTime()) / 1000,
    )
    return `${seconds}s`
}

export const formatStreamTimestamp = (date: DateInput): string => (
    formatDate(date, DATE_FORMATS.STREAM_TIMESTAMP)
)

/**
 * Epoch ms for a naive UTC timestamp ("YYYY-MM-DDTHH:MM:SS", no zone) by
 * appending 'Z' before parsing — the backend formats timestamps
 * `AT TIME ZONE 'UTC'` without an offset, so the default (local-time) Date
 * parse would be wrong. Returns null when unparseable.
 */
export const parseNaiveUtcEpoch = (timestamp: string | null | undefined): number | null => {
    if (typeof timestamp !== 'string' || timestamp.length < 16) {
        return null
    }
    const ms = new Date(`${timestamp}Z`).getTime()
    return Number.isNaN(ms) ? null : ms
}

/**
 * HH:MM slice of an ISO-ish timestamp string, or '--' when too short or not
 * a string. Used for compact per-minute chart/report labels where a full
 * date parse is unnecessary.
 */
export const formatClockTime = (timestamp: unknown): string => (
    typeof timestamp === 'string' && timestamp.length >= 16 ? timestamp.slice(11, 16) : '--'
)
