/**
 * Error handling utilities
 * 
 * This module provides utilities for handling, formatting, and categorizing
 * errors throughout the application.
 */

import { ERROR_MESSAGES } from '../constants'

/**
 * Error types for categorization
 */
export const ERROR_TYPES = {
    NETWORK: 'network',
    VALIDATION: 'validation',
    AUTHENTICATION: 'authentication',
    AUTHORIZATION: 'authorization',
    NOT_FOUND: 'not_found',
    SERVER: 'server',
    CLIENT: 'client',
    UNKNOWN: 'unknown',
}

/**
 * Determines the error type based on error object
 * @param {Error|object} error - The error object
 * @returns {string} Error type
 */
// Helper function to categorize by HTTP status
const categorizeByStatus = status => {
    if (status === 400) {
        return ERROR_TYPES.VALIDATION
    }
    if (status === 401) {
        return ERROR_TYPES.AUTHENTICATION
    }
    if (status === 403) {
        return ERROR_TYPES.AUTHORIZATION
    }
    if (status === 404) {
        return ERROR_TYPES.NOT_FOUND
    }
    if (status >= 500) {
        return ERROR_TYPES.SERVER
    }
    if (status >= 400) {
        return ERROR_TYPES.CLIENT
    }
    return ERROR_TYPES.UNKNOWN
}

export const getErrorType = error => {
    if (!error) {
        return ERROR_TYPES.UNKNOWN
    }

    // Network errors
    if (error.code === 'NETWORK_ERROR' || error.message?.includes('Network Error')) {
        return ERROR_TYPES.NETWORK
    }

    // HTTP status code based categorization
    if (error.response?.status) {
        return categorizeByStatus(error.response.status)
    }

    return ERROR_TYPES.UNKNOWN
}

/**
 * Extracts error message from various error object formats
 * @param {Error|object} error - The error object
 * @returns {string|null} Extracted message or null if none found
 */
const extractErrorMessage = error => {
    const message = error.response?.data?.message ||
                   error.response?.data?.error ||
                   error.message ||
                   error.toString()

    return (typeof message === 'string' && message.trim()) ? message : null
}

/**
 * Gets fallback error message based on error type
 * @param {string} errorType - The categorized error type
 * @param {string} defaultMessage - Default fallback message
 * @returns {string} Appropriate error message
 */
const getFallbackMessage = (errorType, defaultMessage) => {
    const typeMessages = {
        [ERROR_TYPES.NETWORK]: ERROR_MESSAGES.NETWORK_ERROR,
        [ERROR_TYPES.VALIDATION]: ERROR_MESSAGES.VALIDATION_ERROR,
        [ERROR_TYPES.AUTHENTICATION]: ERROR_MESSAGES.UNAUTHORIZED,
        [ERROR_TYPES.AUTHORIZATION]: ERROR_MESSAGES.UNAUTHORIZED,
        [ERROR_TYPES.NOT_FOUND]: ERROR_MESSAGES.NOT_FOUND,
        [ERROR_TYPES.SERVER]: ERROR_MESSAGES.API_ERROR,
    }

    return typeMessages[errorType] || defaultMessage
}

/**
 * Formats error message for user display
 * @param {Error|object} error - The error object
 * @param {string} defaultMessage - Default message if none can be extracted
 * @returns {string} Formatted error message
 */
export const formatErrorMessage = (error, defaultMessage = ERROR_MESSAGES.UNKNOWN_ERROR) => {
    if (!error) {
        return defaultMessage
    }

    // Try to extract message from error object
    const extractedMessage = extractErrorMessage(error)
    if (extractedMessage) {
        return extractedMessage
    }

    // Fallback to error type specific messages
    const errorType = getErrorType(error)
    return getFallbackMessage(errorType, defaultMessage)
}

/**
 * Determines if an error is retryable
 * @param {Error|object} error - The error object
 * @returns {boolean} Whether the error is retryable
 */
export const isRetryableError = error => {
    const errorType = getErrorType(error)
    const status = error.response?.status

    // Network errors are generally retryable
    if (errorType === ERROR_TYPES.NETWORK) {
        return true
    }

    // Server errors (5xx) are often retryable
    if (status >= 500) {
        return true
    }

    // Rate limiting (429) is retryable with backoff
    if (status === 429) {
        return true
    }

    // Temporary redirects might be retryable
    if (status === 307 || status === 308) {
        return true
    }

    return false
}

/**
 * Gets retry delay based on attempt number and error type
 * @param {number} attemptNumber - Current attempt number (1-based)
 * @param {Error|object} error - The error object
 * @returns {number} Delay in milliseconds
 */
export const getRetryDelay = (attemptNumber, _error) => {
    const baseDelay = 1000 // 1 second
    const maxDelay = 30000 // 30 seconds

    // Exponential backoff: delay = baseDelay * (2 ^ (attempt - 1))
    const delay = baseDelay * Math.pow(2, attemptNumber - 1)

    // Add some jitter to prevent thundering herd
    const jitter = Math.random() * 1000

    return Math.min(delay + jitter, maxDelay)
}

/**
 * Logs error with contextual information
 * @param {Error|object} error - The error object
 * @param {string} context - Context where error occurred
 * @param {object} additionalInfo - Additional information to log
 */
export const logError = (error, context = 'Unknown', additionalInfo = {}) => {
    const errorInfo = {
        context,
        type: getErrorType(error),
        message: formatErrorMessage(error),
        timestamp: new Date().toISOString(),
        ...additionalInfo,
    }

    if (error.response) {
        errorInfo.status = error.response.status
        errorInfo.statusText = error.response.statusText
        errorInfo.url = error.response.config?.url
        errorInfo.method = error.response.config?.method
    }

    if (error.stack) {
        errorInfo.stack = error.stack
    }

    console.error('Error logged:', errorInfo)

    // In production, you might want to send this to an error tracking service
    // Example: Sentry.captureException(error, { extra: errorInfo })
}

/**
 * Creates a user-friendly error object
 * @param {Error|object} error - The original error
 * @param {string} context - Context where error occurred
 * @returns {object} User-friendly error object
 */
export const createUserError = (error, context) => ({
    type: getErrorType(error),
    message: formatErrorMessage(error),
    retryable: isRetryableError(error),
    context,
    timestamp: new Date().toISOString(),
    originalError: error,
})

/**
 * Error boundary helper for catching async errors
 * @param {Promise} promise - Promise to wrap
 * @param {string} context - Context for error logging
 * @returns {Promise} Promise that logs errors before rejecting
 */
export const withErrorLogging = async (promise, context) => {
    try {
        return await promise
    } catch (error) {
        logError(error, context)
        throw error
    }
}
