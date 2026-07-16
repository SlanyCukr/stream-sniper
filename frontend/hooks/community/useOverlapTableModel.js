import {
    useMemo,
} from 'react'
import { useTableSort } from '@/hooks/useTableSort'
import { compareNullable } from '@/utils/sortUtils'

const rowValue = (row, sort) => {
    if (sort === 'a') return row.aName.toLowerCase()
    if (sort === 'b') return row.bName.toLowerCase()
    return sort === 'jaccard' ? row.jaccard : row.shared
}

const defaultSortDirection = key => (
    key === 'a' || key === 'b' ? 'asc' : 'desc'
)

export const useOverlapTableModel = ({
    rows,
}) => {
    const { sort, dir, onSort } = useTableSort({
        initialKey: 'jaccard',
        initialDirection: 'desc',
        getDefaultDirection: defaultSortDirection,
    })
    const sortedRows = useMemo(() => {
        return [...rows].sort((left, right) => {
            const leftValue = rowValue(left, sort)
            const rightValue = rowValue(right, sort)
            return compareNullable(leftValue, rightValue, dir)
        })
    }, [rows, sort, dir])
    return {
        sort,
        dir,
        sortedRows,
        handleSort: onSort,
    }
}
