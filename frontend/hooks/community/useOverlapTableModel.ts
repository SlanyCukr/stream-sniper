import {
    useMemo,
} from 'react'
import { useTableSort } from '@/hooks/useTableSort'
import { compareNullable } from '@/utils/sortUtils'
import type { OverlapRow } from './useOverlapModel'

type SortKey = 'a' | 'b' | 'jaccard' | 'shared'

const rowValue = (row: OverlapRow, sort: SortKey): string | number | null => {
    if (sort === 'a') return row.aName.toLowerCase()
    if (sort === 'b') return row.bName.toLowerCase()
    return sort === 'jaccard' ? row.jaccard : row.shared
}

const defaultSortDirection = (key: SortKey): 'asc' | 'desc' => (
    key === 'a' || key === 'b' ? 'asc' : 'desc'
)

interface UseOverlapTableModelOptions {
    rows: OverlapRow[]
}

export const useOverlapTableModel = ({
    rows,
}: UseOverlapTableModelOptions) => {
    const { sort, dir, onSort } = useTableSort({
        initialKey: 'jaccard' as SortKey,
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
