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

/** @param {Date|string|number} date */
export const formatStreamTimestamp = date => formatDate(date, DATE_FORMATS.STREAM_TIMESTAMP)

/** @param {Date|string|number} date */
export const isValidDate = date => validDateOrNull(date) !== null
