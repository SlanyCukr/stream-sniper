import {
    useCallback, useState,
} from 'react'

/** @typedef {'asc'|'desc'} SortDirection */

/**
 * @template {string} Key
 * @param {{
 * initialKey: Key,
 * initialDirection: SortDirection,
 * getDefaultDirection: (key: Key) => SortDirection,
 * }} options
 */
export const useTableSort = ({
    initialKey,
    initialDirection,
    getDefaultDirection,
}) => {
    const [sort, setSort] = useState(initialKey)
    const [dir, setDir] = useState(initialDirection)

    const onSort = useCallback((/** @type {Key} */ key) => {
        if (sort === key) {
            setDir(previous => (previous === 'asc' ? 'desc' : 'asc'))
            return
        }
        setSort(key)
        setDir(getDefaultDirection(key))
    }, [sort, getDefaultDirection])

    return { sort, dir, onSort }
}
