import { useQuery } from '@tanstack/react-query'
import { retrieveCreatorHeadToHead } from '@/lib/api/community'
import {
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

export interface HeadToHeadSide {
    creatorId: number
    nick: string
    displayName: string
    chatters: number
    regulars: number
    /** This side's overlap share of its own audience; null when the audience is empty (unknown, not 0). */
    sharedChatterShare: number | null
    sharedRegularShare: number | null
}

export interface CreatorHeadToHead {
    /** Side `a` is always the lower creator id — the payload is param-order independent. */
    a: HeadToHeadSide
    b: HeadToHeadSide
    sharedChatters: number
    sharedRegulars: number
    jaccardChatters: number | null
    jaccardRegulars: number | null
    computedAt: string | null
}

const headToHeadKeys = {
    all: ['community', 'head-to-head'] as const,
    pair: (a: number, b: number) => {
        // Normalize like the backend cache so (a,b) and (b,a) share one cache entry.
        const [lo, hi] = a < b ? [a, b] : [b, a]
        return [...headToHeadKeys.all, { a: lo, b: hi }] as const
    },
}

const mapSide = (value: unknown, label: string): HeadToHeadSide => {
    const side = requireRecord(value, label)
    return {
        creatorId: requireFiniteNumberField(side, 'creator_id', label),
        nick: requireStringField(side, 'nick', label),
        displayName: requireStringField(side, 'display_name', label),
        chatters: requireFiniteNumberField(side, 'chatters', label),
        regulars: requireFiniteNumberField(side, 'regulars', label),
        sharedChatterShare: requireNullableFiniteNumberField(side, 'shared_chatter_share', label),
        sharedRegularShare: requireNullableFiniteNumberField(side, 'shared_regular_share', label),
    }
}

export const mapCreatorHeadToHead = (value: unknown): CreatorHeadToHead => {
    const data = requireRecord(value, 'creator head-to-head')
    return {
        a: mapSide(data.a, 'creator head-to-head.a'),
        b: mapSide(data.b, 'creator head-to-head.b'),
        sharedChatters: requireFiniteNumberField(data, 'shared_chatters', 'creator head-to-head'),
        sharedRegulars: requireFiniteNumberField(data, 'shared_regulars', 'creator head-to-head'),
        jaccardChatters: requireNullableFiniteNumberField(data, 'jaccard_chatters', 'creator head-to-head'),
        jaccardRegulars: requireNullableFiniteNumberField(data, 'jaccard_regulars', 'creator head-to-head'),
        computedAt: requireNullableStringField(data, 'computed_at', 'creator head-to-head'),
    }
}

export const useCreatorHeadToHead = (
    creatorA: number | null,
    creatorB: number | null,
    { enabled = true }: { enabled?: boolean } = {},
) => useQuery({
    queryKey: creatorA && creatorB
        ? headToHeadKeys.pair(creatorA, creatorB)
        : [...headToHeadKeys.all, { a: creatorA, b: creatorB }],
    queryFn: async () => mapCreatorHeadToHead(
        await retrieveCreatorHeadToHead(creatorA as number, creatorB as number),
    ),
    enabled: enabled && Boolean(creatorA) && Boolean(creatorB) && creatorA !== creatorB,
})
