/**
 * Date utility functions using date-fns
 * 
 * This module provides date formatting and manipulation functions
 * as a replacement for Moment.js throughout the application.
 */

import {
    format, formatDistanceToNow, intervalToDuration,
} from 'date-fns'
import { DATE_FORMATS } from '../constants'

/**
 * Formats a date using the specified format pattern
 * @param {Date|string|number} date - The date to format
 * @param {string} formatPattern - The format pattern (from DATE_FORMATS or custom)
 * @returns {string} Formatted date string
 */
export const formatDate = (date, formatPattern = DATE_FORMATS.LONG) => {
    try {
        const dateObj = typeof date === 'string' ? new Date(date) : date
        return format(dateObj, formatPattern)
    } catch (error) {
        console.error('Error formatting date:', error)
        return 'Invalid date'
    }
}

/**
 * Returns the relative time from now (e.g., "3 hours ago")
 * @param {Date|string|number} date - The date to compare with now
 * @param {object} options - Options for formatting
 * @returns {string} Relative time string
 */
export const formatTimeAgo = (date, options = {}) => {
    try {
        const dateObj = typeof date === 'string' ? new Date(date) : date
        return formatDistanceToNow(dateObj, {
            addSuffix: true,
            ...options,
        })
    } catch (error) {
        console.error('Error formatting relative time:', error)
        return 'Invalid date'
    }
}

/**
 * Calculates and formats the duration between two dates
 * @param {Date|string|number} startDate - Start date
 * @param {Date|string|number} endDate - End date
 * @param {object} options - Formatting options
 * @returns {string} Formatted duration string
 */
// Helper function to build duration parts
const buildDurationParts = duration => {
    const {
        years,
        months,
        days,
        hours,
        minutes,
        seconds,
    } = duration

    const parts = [
    ]

    if (years > 0) {
        parts.push(`${years}y`)
    }
    if (months > 0) {
        parts.push(`${months}mo`)
    }
    if (days > 0) {
        parts.push(`${days}d`)
    }
    if (hours > 0) {
        parts.push(`${hours}h`)
    }
    if (minutes > 0) {
        parts.push(`${minutes}m`)
    }
    if (seconds > 0 || parts.length === 0) {
        parts.push(`${seconds}s`)
    }

    return parts
}

export const formatDurationBetween = (startDate, endDate) => {
    try {
        const start = typeof startDate === 'string' ? new Date(startDate) : startDate
        const end = typeof endDate === 'string' ? new Date(endDate) : endDate

        const duration = intervalToDuration({
            start,
            end,
        })

        const parts = buildDurationParts(duration)
        return parts.join(' ')
    } catch (error) {
        console.error('Error calculating duration:', error)
        return 'Invalid duration'
    }
}

/**
 * Formats a date to match the stream timestamp format
 * @param {Date|string|number} date - The date to format
 * @returns {string} Formatted timestamp
 */
export const formatStreamTimestamp = date => formatDate(date, DATE_FORMATS.STREAM_TIMESTAMP)

/**
 * Utility to parse various date inputs safely
 * @param {Date|string|number} dateInput - The date input to parse
 * @returns {Date} Parsed Date object
 */
export const parseDate = dateInput => {
    if (dateInput instanceof Date) {
        return dateInput
    }

    if (typeof dateInput === 'string' || typeof dateInput === 'number') {
        return new Date(dateInput)
    }

    throw new Error('Invalid date input')
}

/**
 * Checks if a date is valid
 * @param {Date|string|number} date - The date to validate
 * @returns {boolean} True if valid, false otherwise
 */
export const isValidDate = date => {
    try {
        const dateObj = parseDate(date)
        return !Number.isNaN(dateObj.getTime())
    } catch (parseError) {
        console.error('Date parsing error:', parseError)
        return false
    }
}
