import {
    useCallback, useMemo,
} from 'react'

/** @typedef {{creatorId:number, nick:string, displayName?:string|null}} OverlapCreator */
/** @typedef {{
 * a:number,
 * b:number,
 * sharedChatters:number,
 * sharedRegulars:number,
 * jaccardChatters:number|null,
 * jaccardRegulars:number|null,
 * }} OverlapPair */
/** @typedef {{aId:number, bId:number}} SelectedPair */
/** @typedef {'chatters'|'regulars'} OverlapMetric */

/** @param {number} firstId @param {number} secondId */
const normalizePair = (firstId, secondId) => ({
    aId: Math.min(firstId, secondId),
    bId: Math.max(firstId, secondId),
})

/** @param {number} firstId @param {number} secondId */
const pairKey = (firstId, secondId) => {
    const pair = normalizePair(firstId, secondId)
    return `${pair.aId}-${pair.bId}`
}

/** @param {{
 * creators: OverlapCreator[],
 * pairs: OverlapPair[],
 * metric: OverlapMetric,
 * selectedPair: SelectedPair|null,
 * onSelectPair: (pair:SelectedPair) => void,
 * }} options */
export const useOverlapModel = ({
    creators, pairs, metric, selectedPair, onSelectPair,
}) => {
    const names = useMemo(() => new Map(creators.map(creator => [
        creator.creatorId,
        creator.displayName || creator.nick || `#${creator.creatorId}`,
    ])), [creators])

    const nameOf = useCallback(
        (/** @type {number} */ creatorId) => names.get(creatorId) || `#${creatorId}`,
        [names],
    )

    const rows = useMemo(() => pairs.map(pair => {
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
        /** @type {number} */ firstId,
        /** @type {number} */ secondId,
    ) => (
        rowsByPair.get(pairKey(firstId, secondId)) || { shared: 0, jaccard: null }
    ), [rowsByPair])

    const selectPair = useCallback((
        /** @type {number} */ firstId,
        /** @type {number} */ secondId,
    ) => {
        if (firstId !== secondId) onSelectPair(normalizePair(firstId, secondId))
    }, [onSelectPair])

    const isSelected = useCallback((
        /** @type {number} */ firstId,
        /** @type {number} */ secondId,
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
