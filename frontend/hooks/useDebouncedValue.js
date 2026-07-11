import {
    useEffect,
    useState,
} from 'react'

/**
 * Returns a debounced copy of `value` that only updates after `ms` of no changes.
 * @param {*} value - The value to debounce
 * @param {number} ms - Debounce delay in milliseconds (default 300)
 * @returns {*} The debounced value
 */
export const useDebouncedValue = (value, ms = 300) => {
    const [
        debounced,
        setDebounced,
    ] = useState(value)

    useEffect(() => {
        const timer = setTimeout(() => setDebounced(value), ms)
        return () => clearTimeout(timer)
    }, [
        value,
        ms,
    ])

    return debounced
}
