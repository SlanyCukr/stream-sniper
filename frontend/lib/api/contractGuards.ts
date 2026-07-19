/**
 * Fail at the API boundary when a required server shape is absent. Optional
 * fields remain the mapper's responsibility; required collections do not
 * silently become an empty-success state.
 */
export const requireRecord = (value: unknown, label: string): Record<string, unknown> => {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
        throw new TypeError(`${label} must be an object`)
    }
    return value as Record<string, unknown>
}

export const requireArrayField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): unknown[] => {
    const value = record[field]
    if (!Array.isArray(value)) {
        throw new TypeError(`${label}.${field} must be an array`)
    }
    return value
}

export const requireArray = (value: unknown, label: string): unknown[] => {
    if (!Array.isArray(value)) {
        throw new TypeError(`${label} must be an array`)
    }
    return value
}

export const requireFiniteNumberField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): number => {
    const value = record[field]
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new TypeError(`${label}.${field} must be a finite number`)
    }
    return value
}

export const requireBooleanField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): boolean => {
    const value = record[field]
    if (typeof value !== 'boolean') {
        throw new TypeError(`${label}.${field} must be a boolean`)
    }
    return value
}

export const requireStringField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): string => {
    const value = record[field]
    if (typeof value !== 'string') {
        throw new TypeError(`${label}.${field} must be a string`)
    }
    return value
}

export const requireStringOrFiniteNumberField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): string | number => {
    const value = record[field]
    if (typeof value === 'string') return value
    if (typeof value === 'number' && Number.isFinite(value)) return value
    throw new TypeError(`${label}.${field} must be a string or finite number`)
}

export const requireNullableFiniteNumberField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): number | null => {
    const value = record[field]
    if (value !== null && (typeof value !== 'number' || !Number.isFinite(value))) {
        throw new TypeError(`${label}.${field} must be a finite number or null`)
    }
    return value
}

export const requireNullableStringField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): string | null => {
    const value = record[field]
    if (value !== null && typeof value !== 'string') {
        throw new TypeError(`${label}.${field} must be a string or null`)
    }
    return value
}

export const requireNullableBooleanField = (
    record: Record<string, unknown>,
    field: string,
    label: string,
): boolean | null => {
    const value = record[field]
    if (value !== null && typeof value !== 'boolean') {
        throw new TypeError(`${label}.${field} must be a boolean or null`)
    }
    return value
}
