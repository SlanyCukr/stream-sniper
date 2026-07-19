import {
    useCallback, useMemo,
} from 'react'
import type { CommunityOverlapPair, OverlapMetric } from './useCommunityQuery'

export interface OverlapCreator {
    creatorId: number
    nick: string
    displayName?: string | null
}

export type OverlapPair = CommunityOverlapPair

export interface SelectedPair {
    aId: number
    bId: number
}

export interface OverlapRow extends OverlapPair {
    aId: number
    bId: number
    aName: string
    bName: string
    shared: number
    jaccard: number | null
}

export interface OverlapCell {
    shared: number
    jaccard: number | null
}

export interface OverlapMatrixModel {
    rows: OverlapRow[]
    nameOf: (creatorId: number) => string
    cellFor: (firstId: number, secondId: number) => OverlapRow | OverlapCell
    onSelectPair: (firstId: number, secondId: number) => void
    isSelected: (firstId: number, secondId: number) => boolean
}

export interface OverlapTableModel {
    rows: OverlapRow[]
    onSelectPair: (firstId: number, secondId: number) => void
    isSelected: (firstId: number, secondId: number) => boolean
}

const normalizePair = (firstId: number, secondId: number): SelectedPair => ({
    aId: Math.min(firstId, secondId),
    bId: Math.max(firstId, secondId),
})

const pairKey = (firstId: number, secondId: number): string => {
    const pair = normalizePair(firstId, secondId)
    return `${pair.aId}-${pair.bId}`
}

interface UseOverlapModelOptions {
    creators: OverlapCreator[]
    pairs: OverlapPair[]
    metric: OverlapMetric
    selectedPair: SelectedPair | null
    onSelectPair: (pair: SelectedPair) => void
}

export const useOverlapModel = ({
    creators, pairs, metric, selectedPair, onSelectPair,
}: UseOverlapModelOptions) => {
    const names = useMemo(() => new Map(creators.map(creator => [
        creator.creatorId,
        creator.displayName || creator.nick || `#${creator.creatorId}`,
    ])), [creators])

    const nameOf = useCallback(
        (creatorId: number) => names.get(creatorId) || `#${creatorId}`,
        [names],
    )

    const rows = useMemo<OverlapRow[]>(() => pairs.map(pair => {
        const { aId, bId } = normalizePair(pair.a, pair.b)
        return {
            ...pair,
            aId,
            bId,
            aName: nameOf(aId),
            bName: nameOf(bId),
            shared: metric === 'chatters' ? pair.sharedChatters : pair.sharedRegulars,
            jaccard: metric === 'chatters' ? pair.jaccardChatters : pair.jaccardRegulars,
        }
    }), [pairs, metric, nameOf])

    const rowsByPair = useMemo(() => new Map(rows.map(row => [
        pairKey(row.aId, row.bId),
        row,
    ])), [rows])

    const cellFor = useCallback((
        firstId: number,
        secondId: number,
    ): OverlapRow | OverlapCell => (
        rowsByPair.get(pairKey(firstId, secondId)) || { shared: 0, jaccard: null }
    ), [rowsByPair])

    const selectPair = useCallback((
        firstId: number,
        secondId: number,
    ) => {
        if (firstId !== secondId) onSelectPair(normalizePair(firstId, secondId))
    }, [onSelectPair])

    const isSelected = useCallback((
        firstId: number,
        secondId: number,
    ) => {
        if (!selectedPair) return false
        return pairKey(firstId, secondId) === pairKey(selectedPair.aId, selectedPair.bId)
    }, [selectedPair])

    const detail = selectedPair
        ? rowsByPair.get(pairKey(selectedPair.aId, selectedPair.bId)) || null
        : null

    return {
        detail,
        matrix: {
            rows,
            nameOf,
            cellFor,
            onSelectPair: selectPair,
            isSelected,
        },
        table: {
            rows,
            onSelectPair: selectPair,
            isSelected,
        },
    }
}
