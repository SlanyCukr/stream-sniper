import {
    useCallback, useMemo, useState,
} from 'react'

export const MATRIX_GEOMETRY = {
    cell: 26,
    labelWidth: 132,
    labelHeight: 132,
}

export const truncateMatrixLabel = (text, max = 20) => (
    text.length > max ? `${text.slice(0, max - 1)}…` : text
)

export const useOverlapMatrixModel = ({
    creators, metric, model,
}) => {
    const [hover, setHover] = useState(null)
    const nameOf = useCallback(
        creator => model.nameOf(creator.creatorId),
        [model],
    )
    const sorted = useMemo(() => {
        const audience = creator => (
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

    const fillOpacity = useCallback(jaccard => (
        jaccard == null || maxJaccard <= 0
            ? 0
            : 0.08 + 0.92 * Math.min(1, jaccard / maxJaccard)
    ), [maxJaccard])

    const handleEnter = useCallback((rowIndex, columnIndex) => {
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

    return {
        hover,
        sorted,
        nameOf,
        cellFor: model.cellFor,
        fillOpacity,
        handleEnter,
        handleLeave: () => setHover(null),
        handleSelect: model.onSelectPair,
        isSelected: model.isSelected,
    }
}
