// @ts-check

import {
    format, formatDistanceToNow, intervalToDuration,
} from 'date-fns'

const DATE_FORMATS = {
    LONG: 'MMMM dd, yyyy HH:mm:ss',
    STREAM_TIMESTAMP: 'yyyy/MM/dd HH:mm:ss',
}

/** @param {Date|string|number} dateInput @returns {Date} */
export const parseDate = dateInput => {
    if (dateInput instanceof Date) return dateInput
    if (typeof dateInput === 'string' || typeof dateInput === 'number') {
        return new Date(dateInput)
    }
    throw new TypeError('Invalid date input')
}

/** @param {Date|string|number} value @returns {Date|null} */
const validDateOrNull = value => {
    try {
        const date = parseDate(value)
        return Number.isNaN(date.getTime()) ? null : date
    } catch {
        return null
    }
}

/** @param {Date|string|number} date @param {string} [formatPattern] */
export const formatDate = (date, formatPattern = DATE_FORMATS.LONG) => {
    const parsed = validDateOrNull(date)
    return parsed ? format(parsed, formatPattern) : 'Invalid date'
}

/** @param {Date|string|number} date @param {object} [options] */
export const formatTimeAgo = (date, options = {}) => {
    const parsed = validDateOrNull(date)
    if (!parsed) return 'Invalid date'
    return formatDistanceToNow(parsed, {
        addSuffix: true,
        ...options,
    }).replace(/^(about|over|almost|less than) /, '')
}

/** @param {import('date-fns').Duration} duration @returns {string[]} */
const buildDurationParts = ({
    years = 0, months = 0, days = 0, hours = 0, minutes = 0, seconds = 0,
}) => {
    const parts = []
    if (years > 0) parts.push(`${years}y`)
    if (months > 0) parts.push(`${months}mo`)
    if (days > 0) parts.push(`${days}d`)
    if (hours > 0) parts.push(`${hours}h`)
    if (minutes > 0) parts.push(`${minutes}m`)
    if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`)
    return parts
}

/**
 * @param {Date|string|number} startDate
 * @param {Date|string|number|null} endDate null means still live
 */
export const formatDurationBetween = (startDate, endDate) => {
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
 * @param {Date|string|number|null|undefined} date
 * @param {string} [fallback]
 */
export const formatDateTime = (date, fallback = 'N/A') => (
    date ? parseDate(date).toLocaleString() : fallback
)

/**
 * Whole-second duration "Ns" between two dates, or a fallback when either
 * is missing. Distinct from formatDurationBetween: no unit breakdown, just
 * whole seconds — used for short-lived processing-job durations.
 * @param {Date|string|number|null|undefined} startDate
 * @param {Date|string|number|null|undefined} endDate
 * @param {string} [fallback]
 */
export const formatDurationSeconds = (startDate, endDate, fallback = 'N/A') => {
    if (!startDate || !endDate) return fallback
    const seconds = Math.floor(
        (parseDate(endDate).getTime() - parseDate(startDate).getTime()) / 1000,
    )
    return `${seconds}s`
}

/** @param {Date|string|number} date */
export const formatStreamTimestamp = date => formatDate(date, DATE_FORMATS.STREAM_TIMESTAMP)

/** @param {Date|string|number} date */
export const isValidDate = date => validDateOrNull(date) !== null

/**
 * Epoch ms for a naive UTC timestamp ("YYYY-MM-DDTHH:MM:SS", no zone) by
 * appending 'Z' before parsing — the backend formats timestamps
 * `AT TIME ZONE 'UTC'` without an offset, so the default (local-time) Date
 * parse would be wrong. Returns null when unparseable.
 * @param {string|null|undefined} timestamp
 * @returns {number|null}
 */
export const parseNaiveUtcEpoch = timestamp => {
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
 * @param {unknown} timestamp
 */
export const formatClockTime = timestamp => (
    typeof timestamp === 'string' && timestamp.length >= 16 ? timestamp.slice(11, 16) : '--'
)
