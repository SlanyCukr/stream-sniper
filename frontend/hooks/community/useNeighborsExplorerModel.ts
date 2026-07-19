import { useMemo } from 'react'
import { useCreatorNeighbors } from './useCommunityQuery'
import type { CommunityCreator, CreatorNeighbor, OverlapMetric } from './useCommunityQuery'

const NEIGHBOR_LIMIT = 10

export interface CreatorOption {
    label: string
    value: number
}

export interface NeighborWithShared extends CreatorNeighbor {
    shared: number
}

interface UseNeighborsExplorerModelOptions {
    creators: CommunityCreator[]
    metric: OverlapMetric
    selected: CreatorOption | null
}

export const useNeighborsExplorerModel = ({
    creators, metric, selected,
}: UseNeighborsExplorerModelOptions) => {
    const options = useMemo<CreatorOption[]>(() => creators.map(creator => ({
        label: creator.displayName || creator.nick || `#${creator.creatorId}`,
        value: creator.creatorId,
    })), [creators])
    const creatorId = selected?.value || null
    const query = useCreatorNeighbors(creatorId, {
        metric,
        limit: NEIGHBOR_LIMIT,
    })
    const neighbors = useMemo<NeighborWithShared[]>(() => (query.data?.neighbors || []).map(neighbor => ({
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
