// @ts-check

const ERROR_MESSAGES = {
    NETWORK_ERROR: "Can't reach the server. Check your connection and try again.",
    API_ERROR: 'The server hit a problem. Try again in a moment.',
    NOT_FOUND: "That page or item doesn't exist. It may have been removed.",
    UNAUTHENTICATED: 'Your session has expired or is invalid. Log in again to continue.',
    FORBIDDEN: "You don't have permission to do this.",
    VALIDATION_ERROR: 'Please check your input and try again.',
    RATE_LIMITED: "You're doing that too fast. Wait a moment and try again.",
    UNKNOWN_ERROR: 'An unexpected error occurred.',
}

const ERROR_TYPES = Object.freeze({
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
/** @typedef {{message:string, type:ErrorType, status:number|null, retryable:boolean, retryAfterSeconds:number|null, detail:unknown}} NormalizedApiError */
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
        // FastAPI prefixes custom validator messages with "Value error, ".
        .map(message => /** @type {string} */ (message).replace(/^Value error, /, ''))
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

/**
 * Read a Retry-After header as whole seconds (numeric form only — the
 * HTTP-date form is ignored). Axios lowercases response header names.
 * @param {unknown} headers
 * @returns {number|null}
 */
const retryAfterSecondsFrom = headers => {
    const raw = asRecord(headers)?.['retry-after']
    const seconds = typeof raw === 'number' ? raw : Number.parseInt(String(raw ?? ''), 10)
    return Number.isFinite(seconds) && seconds >= 0 ? seconds : null
}

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
    [ERROR_TYPES.AUTHENTICATION]: ERROR_MESSAGES.UNAUTHENTICATED,
    [ERROR_TYPES.AUTHORIZATION]: ERROR_MESSAGES.FORBIDDEN,
    [ERROR_TYPES.NOT_FOUND]: ERROR_MESSAGES.NOT_FOUND,
    [ERROR_TYPES.SERVER]: ERROR_MESSAGES.API_ERROR,
    [ERROR_TYPES.CLIENT]: fallback,
    [ERROR_TYPES.UNKNOWN]: fallback,
}[type] || fallback)

/**
 * Create an Error whose message is written for end users and safe to render.
 * `normalizeApiError` only surfaces `.message` from errors marked this way —
 * unmarked native errors (TypeErrors, contract guards, library failures) fall
 * back to sanitized copy instead.
 * @param {string} message
 * @returns {Error & {userFacing: true}}
 */
export const uiError = message => Object.assign(new Error(message), { userFacing: /** @type {const} */ (true) })

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
    const retryAfterSeconds = status === 429 ? retryAfterSecondsFrom(response?.headers) : null
    const rateLimitedMessage = status !== 429
        ? null
        : retryAfterSeconds
            ? `You're doing that too fast. Try again in ${retryAfterSeconds} second${retryAfterSeconds === 1 ? '' : 's'}.`
            : ERROR_MESSAGES.RATE_LIMITED
    // Only errors explicitly marked user-facing may surface their raw message;
    // everything else (TypeErrors, contract guards, library errors) is sanitized.
    const userFacingMessage = source?.userFacing === true ? nativeMessage : null
    const message = rateLimitedMessage
        || userFacingMessage
        || detailMessage(detail)
        || nonEmptyString(payload?.message)
        || nonEmptyString(payload?.error)
        || categorizedFallback
        || fallbackMessage(type, fallback)

    return {
        message,
        type,
        status,
        retryable: isRetryable(type, status),
        retryAfterSeconds,
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
