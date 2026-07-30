import {
    retrieveCommunityOverlap,
    retrieveCreatorNeighbors,
} from '@/lib/api/community'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { defineGatedQuery, defineQuery, type QueryOptions } from '@/hooks/defineQuery'

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

const mapCommunityOverlap = (value: unknown): CommunityOverlap => {
    const data = requireRecord(value, 'community overlap')
    return {
        creators: requireArrayField(data, 'creators', 'community overlap').map((value, index) => {
            const label = `community overlap.creators[${index}]`
            const creator = requireRecord(value, label)
            return {
                creatorId: requireFiniteNumberField(creator, 'creator_id', label),
                nick: requireStringField(creator, 'nick', label),
                displayName: requireStringField(creator, 'display_name', label),
                chatters: requireFiniteNumberField(creator, 'chatters', label),
                regulars: requireFiniteNumberField(creator, 'regulars', label),
            }
        }),
        pairs: requireArrayField(data, 'pairs', 'community overlap').map((value, index) => {
            const label = `community overlap.pairs[${index}]`
            const pair = requireRecord(value, label)
            return {
                a: requireFiniteNumberField(pair, 'a', label),
                b: requireFiniteNumberField(pair, 'b', label),
                sharedChatters: requireFiniteNumberField(pair, 'shared_chatters', label),
                sharedRegulars: requireFiniteNumberField(pair, 'shared_regulars', label),
                jaccardChatters: requireNullableFiniteNumberField(pair, 'jaccard_chatters', label),
                jaccardRegulars: requireNullableFiniteNumberField(pair, 'jaccard_regulars', label),
            }
        }),
        computedAt: requireNullableStringField(data, 'computed_at', 'community overlap'),
    }
}

const mapCreatorNeighbors = (value: unknown): CreatorNeighbors => {
    const data = requireRecord(value, 'creator neighbors')
    return {
        neighbors: requireArrayField(data, 'neighbors', 'creator neighbors').map((value, index) => {
            const label = `creator neighbors.neighbors[${index}]`
            const neighbor = requireRecord(value, label)
            return {
                creatorId: requireFiniteNumberField(neighbor, 'creator_id', label),
                nick: requireStringField(neighbor, 'nick', label),
                displayName: requireStringField(neighbor, 'display_name', label),
                sharedChatters: requireFiniteNumberField(neighbor, 'shared_chatters', label),
                sharedRegulars: requireFiniteNumberField(neighbor, 'shared_regulars', label),
            }
        }),
    }
}

const communityOverlapQuery = defineQuery({
    key: (limit: number) => communityKeys.overlap(limit),
    fetch: retrieveCommunityOverlap,
    map: mapCommunityOverlap,
})

export const useCommunityOverlap = (
    { limit = 40 }: { limit?: number } = {},
    options: QueryOptions<CommunityOverlap> = {},
) => communityOverlapQuery(limit, options)

const creatorNeighborsQuery = defineGatedQuery({
    label: 'creator neighbors',
    key: ({ creatorId, metric, limit }: { creatorId: number | null, metric?: OverlapMetric, limit?: number }) => (
        communityKeys.neighbors(creatorId, metric, limit)
    ),
    validate: ({ creatorId, metric, limit }) => (
        creatorId !== null && creatorId > 0 ? { creatorId, metric, limit } : null
    ),
    fetch: ({ creatorId, metric, limit }) => retrieveCreatorNeighbors(creatorId, { metric, limit }),
    map: mapCreatorNeighbors,
})

export const useCreatorNeighbors = (
    creatorId: number | null,
    { metric, limit }: { metric?: OverlapMetric, limit?: number } = {},
    options: QueryOptions<CreatorNeighbors> = {},
) => creatorNeighborsQuery({ creatorId, metric, limit }, options)
