import {
    useCallback, useMemo, useState,
} from 'react'
import type { OverlapMetric } from './useCommunityQuery'
import type { OverlapMatrixModel } from './useOverlapModel'

export const MATRIX_GEOMETRY = {
    cell: 26,
    labelWidth: 132,
    labelHeight: 132,
}

export const truncateMatrixLabel = (text: string, max = 20): string => (
    text.length > max ? `${text.slice(0, max - 1)}…` : text
)

export interface OverlapMatrixCreator {
    creatorId: number
    chatters: number
    regulars: number
}

interface HoverState {
    rowIndex: number
    columnIndex: number
    row: OverlapMatrixCreator
    column: OverlapMatrixCreator
    shared: number
    jaccard: number | null
}

interface UseOverlapMatrixModelOptions {
    creators: OverlapMatrixCreator[]
    metric: OverlapMetric
    model: OverlapMatrixModel
}

export const useOverlapMatrixModel = ({
    creators, metric, model,
}: UseOverlapMatrixModelOptions) => {
    const [hover, setHover] = useState<HoverState | null>(null)
    const nameOf = useCallback(
        (creator: OverlapMatrixCreator) => model.nameOf(creator.creatorId),
        [model],
    )
    const sorted = useMemo(() => {
        const audience = (creator: OverlapMatrixCreator) => (
            metric === 'chatters' ? creator.chatters : creator.regulars
        ) || 0
        return [...creators].sort(
            (first, second) => audience(second) - audience(first) || first.creatorId - second.creatorId,
        )
    }, [creators, metric])

    const maxJaccard = useMemo(() => Math.max(
        0,
        ...model.rows.map(value => value.jaccard ?? 0),
    ), [model.rows])

    const fillOpacity = useCallback((jaccard: number | null) => (
        jaccard == null || maxJaccard <= 0
            ? 0
            : 0.08 + 0.92 * Math.min(1, jaccard / maxJaccard)
    ), [maxJaccard])

    const handleEnter = useCallback((rowIndex: number, columnIndex: number) => {
        const row = sorted[rowIndex]
        const column = sorted[columnIndex]
        const cell = model.cellFor(row.creatorId, column.creatorId)
        setHover({
            rowIndex,
            columnIndex,
            row,
            column,
            shared: cell?.shared ?? 0,
            jaccard: cell?.jaccard ?? null,
        })
    }, [sorted, model])

    // Stable identity so memoized cells don't re-render on every hover change.
    const handleLeave = useCallback(() => setHover(null), [])

    return {
        hover,
        sorted,
        nameOf,
        cellFor: model.cellFor,
        fillOpacity,
        handleEnter,
        handleLeave,
        handleSelect: model.onSelectPair,
        isSelected: model.isSelected,
    }
}
