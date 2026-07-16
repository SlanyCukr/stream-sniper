/**
 * Fail at the API boundary when a required server shape is absent. Optional
 * fields remain the mapper's responsibility; required collections do not
 * silently become an empty-success state.
 * @param {unknown} value
 * @param {string} label
 * @returns {Record<string, unknown>}
 */
export const requireRecord = (value, label) => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new TypeError(`${label} must be an object`)
    }
    return /** @type {Record<string, unknown>} */ (value)
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {unknown[]}
 */
export const requireArrayField = (record, field, label) => {
    const value = record[field]
    if (!Array.isArray(value)) {
        throw new TypeError(`${label}.${field} must be an array`)
    }
    return value
}

/**
 * @param {unknown} value
 * @param {string} label
 * @returns {unknown[]}
 */
export const requireArray = (value, label) => {
    if (!Array.isArray(value)) {
        throw new TypeError(`${label} must be an array`)
    }
    return value
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {number}
 */
export const requireFiniteNumberField = (record, field, label) => {
    const value = record[field]
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new TypeError(`${label}.${field} must be a finite number`)
    }
    return value
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {boolean}
 */
export const requireBooleanField = (record, field, label) => {
    const value = record[field]
    if (typeof value !== 'boolean') {
        throw new TypeError(`${label}.${field} must be a boolean`)
    }
    return value
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {string}
 */
export const requireStringField = (record, field, label) => {
    const value = record[field]
    if (typeof value !== 'string') {
        throw new TypeError(`${label}.${field} must be a string`)
    }
    return value
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {string|number}
 */
export const requireStringOrFiniteNumberField = (record, field, label) => {
    const value = record[field]
    if (typeof value === 'string') return value
    if (typeof value === 'number' && Number.isFinite(value)) return value
    throw new TypeError(`${label}.${field} must be a string or finite number`)
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {number|null}
 */
export const requireNullableFiniteNumberField = (record, field, label) => {
    const value = record[field]
    if (value !== null && (typeof value !== 'number' || !Number.isFinite(value))) {
        throw new TypeError(`${label}.${field} must be a finite number or null`)
    }
    return value
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {string|null}
 */
export const requireNullableStringField = (record, field, label) => {
    const value = record[field]
    if (value !== null && typeof value !== 'string') {
        throw new TypeError(`${label}.${field} must be a string or null`)
    }
    return value
}

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 * @returns {boolean|null}
 */
export const requireNullableBooleanField = (record, field, label) => {
    const value = record[field]
    if (value !== null && typeof value !== 'boolean') {
        throw new TypeError(`${label}.${field} must be a boolean or null`)
    }
    return value
}
