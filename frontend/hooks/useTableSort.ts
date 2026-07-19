import {
    useCallback, useState,
} from 'react'

export type SortDirection = 'asc' | 'desc'

interface UseTableSortOptions<Key extends string> {
    initialKey: Key
    initialDirection: SortDirection
    getDefaultDirection: (key: Key) => SortDirection
}

export const useTableSort = <Key extends string>({
    initialKey,
    initialDirection,
    getDefaultDirection,
}: UseTableSortOptions<Key>) => {
    const [sort, setSort] = useState<Key>(initialKey)
    const [dir, setDir] = useState<SortDirection>(initialDirection)

    const onSort = useCallback((key: Key) => {
        if (sort === key) {
            setDir(previous => (previous === 'asc' ? 'desc' : 'asc'))
            return
        }
        setSort(key)
        setDir(getDefaultDirection(key))
    }, [sort, getDefaultDirection])

    return { sort, dir, onSort }
}
