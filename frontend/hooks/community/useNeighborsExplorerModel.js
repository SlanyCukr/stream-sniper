import { useMemo } from 'react'
import { useCreatorNeighbors } from './useCommunityQuery'

const NEIGHBOR_LIMIT = 10

export const useNeighborsExplorerModel = ({
    creators, metric, selected,
}) => {
    const options = useMemo(() => creators.map(creator => ({
        label: creator.displayName || creator.nick || `#${creator.creatorId}`,
        value: creator.creatorId,
    })), [creators])
    const creatorId = selected?.value || null
    const query = useCreatorNeighbors(creatorId, {
        metric,
        limit: NEIGHBOR_LIMIT,
    })
    const neighbors = useMemo(() => (query.data?.neighbors || []).map(neighbor => ({
        ...neighbor,
        shared: metric === 'chatters' ? neighbor.sharedChatters : neighbor.sharedRegulars,
    })), [query.data, metric])

    return {
        options,
        creatorId,
        query,
        neighbors,
        maxShared: Math.max(1, ...neighbors.map(neighbor => neighbor.shared || 0)),
    }
}
