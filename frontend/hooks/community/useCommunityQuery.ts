import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveCommunityOverlap,
    retrieveCreatorNeighbors,
} from '@/lib/api/community'
import type { OverlapCreatorDto, OverlapPairDto, CreatorNeighborDto } from '@/lib/api/community'
import { requireArrayField, requireRecord } from '@/lib/api/contractGuards'

export type OverlapMetric = 'chatters' | 'regulars'

export interface CommunityCreator {
    creatorId: number
    nick: string
    displayName: string
    chatters: number
    regulars: number
}

export interface CommunityOverlapPair {
    a: number
    b: number
    sharedChatters: number
    sharedRegulars: number
    jaccardChatters: number | null
    jaccardRegulars: number | null
}

export interface CommunityOverlap {
    creators: CommunityCreator[]
    pairs: CommunityOverlapPair[]
    computedAt: string | null
}

export interface CreatorNeighbor {
    creatorId: number
    nick: string
    displayName: string
    sharedChatters: number
    sharedRegulars: number
}

export interface CreatorNeighbors {
    neighbors: CreatorNeighbor[]
}

const communityKeys = {
    all: ['community'] as const,
    overlap: (limit: number) => [...communityKeys.all, 'overlap', { limit }] as const,
    neighbors: (creatorId: number | null, metric: OverlapMetric | undefined, limit: number | undefined) => [
        ...communityKeys.all,
        'neighbors',
        { creatorId, metric, limit },
    ] as const,
}

type QueryOptions<T> = Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, 'queryKey' | 'queryFn'>

export const useCommunityOverlap = (
    { limit = 40 }: { limit?: number } = {},
    options: QueryOptions<CommunityOverlap> = {},
) => useQuery({
    ...options,
    queryKey: communityKeys.overlap(limit),
    queryFn: async (): Promise<CommunityOverlap> => {
        const response = await retrieveCommunityOverlap(limit)
        const data = requireRecord(response.data, 'community overlap')
        // Element shape isn't re-validated per item here, matching pre-migration behavior.
        const creators = requireArrayField(data, 'creators', 'community overlap') as OverlapCreatorDto[]
        const pairs = requireArrayField(data, 'pairs', 'community overlap') as OverlapPairDto[]
        return {
            creators: creators.map(c => ({
                creatorId: c.creator_id,
                nick: c.nick,
                displayName: c.display_name,
                chatters: c.chatters,
                regulars: c.regulars,
            })),
            pairs: pairs.map(p => ({
                a: p.a,
                b: p.b,
                sharedChatters: p.shared_chatters,
                sharedRegulars: p.shared_regulars,
                jaccardChatters: p.jaccard_chatters,
                jaccardRegulars: p.jaccard_regulars,
            })),
            // Not validated pre-migration either — cast preserves that.
            computedAt: data.computed_at as string | null,
        }
    },
})

export const useCreatorNeighbors = (
    creatorId: number | null,
    { metric, limit }: { metric?: OverlapMetric, limit?: number } = {},
    { enabled = true, ...options }: QueryOptions<CreatorNeighbors> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: communityKeys.neighbors(creatorId, metric, limit),
    queryFn: async (): Promise<CreatorNeighbors> => {
        // creatorId is guaranteed non-null here — `enabled` below gates the query.
        const response = await retrieveCreatorNeighbors(creatorId as number, { metric, limit })
        const data = requireRecord(response.data, 'creator neighbors')
        const neighbors = requireArrayField(data, 'neighbors', 'creator neighbors') as CreatorNeighborDto[]
        return {
            neighbors: neighbors.map(n => ({
                creatorId: n.creator_id,
                nick: n.nick,
                displayName: n.display_name,
                sharedChatters: n.shared_chatters,
                sharedRegulars: n.shared_regulars,
            })),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
