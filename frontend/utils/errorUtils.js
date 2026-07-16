// @ts-check

const ERROR_MESSAGES = {
    NETWORK_ERROR: 'Network error occurred. Please check your connection.',
    API_ERROR: 'Server error occurred. Please try again later.',
    NOT_FOUND: 'The requested resource was not found.',
    UNAUTHORIZED: 'You are not authorized to access this resource.',
    VALIDATION_ERROR: 'Please check your input and try again.',
    UNKNOWN_ERROR: 'An unexpected error occurred.',
}

export const ERROR_TYPES = Object.freeze({
    NETWORK: 'network',
    VALIDATION: 'validation',
    AUTHENTICATION: 'authentication',
    AUTHORIZATION: 'authorization',
    NOT_FOUND: 'not_found',
    SERVER: 'server',
    CLIENT: 'client',
    UNKNOWN: 'unknown',
})

/** @typedef {'network'|'validation'|'authentication'|'authorization'|'not_found'|'server'|'client'|'unknown'} ErrorType */
/** @typedef {{message:string, type:ErrorType, status:number|null, retryable:boolean, detail:unknown}} NormalizedApiError */
/** @typedef {{error:unknown, normalized:NormalizedApiError}} UiFailure */

/** @param {unknown} value @returns {Record<string, unknown>|null} */
const asRecord = value => (
    typeof value === 'object' && value !== null
        ? /** @type {Record<string, unknown>} */ (value)
        : null
)

/** @param {unknown} value @returns {string|null} */
const nonEmptyString = value => (
    typeof value === 'string' && value.trim() ? value.trim() : null
)

/** @param {unknown} detail @returns {string|null} */
const detailMessage = detail => {
    const direct = nonEmptyString(detail)
    if (direct) {
        return direct
    }
    if (!Array.isArray(detail)) {
        return null
    }

    const messages = detail
        .map(item => nonEmptyString(asRecord(item)?.msg) || nonEmptyString(item))
        .filter(Boolean)
    return messages.length ? messages.join('; ') : null
}

/** @param {number|null} status @returns {ErrorType} */
const categorizeStatus = status => {
    if (status === 400 || status === 422) return ERROR_TYPES.VALIDATION
    if (status === 401) return ERROR_TYPES.AUTHENTICATION
    if (status === 403) return ERROR_TYPES.AUTHORIZATION
    if (status === 404) return ERROR_TYPES.NOT_FOUND
    if (status !== null && status >= 500) return ERROR_TYPES.SERVER
    if (status !== null && status >= 400) return ERROR_TYPES.CLIENT
    return ERROR_TYPES.UNKNOWN
}

/** @param {number|null} status @param {string|null} code @param {string|null} message */
const isNetworkFailure = (status, code, message) => (
    status === null && (
        code === 'ERR_NETWORK'
        || code === 'NETWORK_ERROR'
        || code === 'ECONNABORTED'
        || Boolean(message && /network error|timeout/i.test(message))
    )
)

/** @param {ErrorType} type @param {number|null} status */
const isRetryable = (type, status) => (
    type === ERROR_TYPES.NETWORK
    || status === 408
    || status === 425
    || status === 429
    || status === 307
    || status === 308
    || Boolean(status && status >= 500)
)

/** @param {ErrorType} type @param {string} fallback */
const fallbackMessage = (type, fallback) => ({
    [ERROR_TYPES.NETWORK]: ERROR_MESSAGES.NETWORK_ERROR,
    [ERROR_TYPES.VALIDATION]: ERROR_MESSAGES.VALIDATION_ERROR,
    [ERROR_TYPES.AUTHENTICATION]: ERROR_MESSAGES.UNAUTHORIZED,
    [ERROR_TYPES.AUTHORIZATION]: ERROR_MESSAGES.UNAUTHORIZED,
    [ERROR_TYPES.NOT_FOUND]: ERROR_MESSAGES.NOT_FOUND,
    [ERROR_TYPES.SERVER]: ERROR_MESSAGES.API_ERROR,
    [ERROR_TYPES.CLIENT]: fallback,
    [ERROR_TYPES.UNKNOWN]: fallback,
}[type] || fallback)

/**
 * Normalize Axios, FastAPI, and native failures once at the UI boundary.
 * @param {unknown} error
 * @param {string} [fallback]
 * @returns {NormalizedApiError}
 */
export const normalizeApiError = (error, fallback = ERROR_MESSAGES.UNKNOWN_ERROR) => {
    const source = asRecord(error)
    const response = asRecord(source?.response)
    const payload = asRecord(response?.data)
    const rawStatus = response?.status
    const status = typeof rawStatus === 'number' ? rawStatus : null
    const code = nonEmptyString(source?.code)
    const nativeMessage = nonEmptyString(source?.message)
    const detail = payload?.detail

    const network = isNetworkFailure(status, code, nativeMessage)
    const type = network ? ERROR_TYPES.NETWORK : categorizeStatus(status)
    const categorizedFallback = status !== null || network
        ? fallbackMessage(type, fallback)
        : null
    const message = detailMessage(detail)
        || nonEmptyString(payload?.message)
        || nonEmptyString(payload?.error)
        || categorizedFallback
        || nativeMessage
        || nonEmptyString(error)
        || fallbackMessage(type, fallback)

    return {
        message,
        type,
        status,
        retryable: isRetryable(type, status),
        detail,
    }
}

/**
 * Keep the original failure for diagnostics while exposing stable UI details.
 * @param {unknown} error
 * @param {string} fallback
 * @param {unknown} [normalizationSource]
 * @returns {UiFailure}
 */
export const toUiFailure = (error, fallback, normalizationSource = error) => ({
    error,
    normalized: normalizeApiError(normalizationSource, fallback),
})
