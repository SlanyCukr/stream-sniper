import { useQuery } from '@tanstack/react-query'
import type { ArchetypeBadge } from '@/components/chatter/ArchetypeBadges'
import { retrieveChatterHeadToHead } from '@/lib/api/chatter'
import {
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { mapArchetypeBadges, mapHomeChannel, type ChatterHomeChannel } from './wireShapes'

export type ChatterVersusHomeChannel = ChatterHomeChannel

export type ChatterVersusArchetype = ArchetypeBadge

export interface ChatterVersusSide {
    chatterId: number
    nick: string
    /** Null = not yet classified (nullable-means-unknown). */
    isBot: boolean | null
    messages: number
    streamsAttended: number
    creatorsVisited: number
    firstSeen: string | null
    lastSeen: string | null
    homeChannel: ChatterVersusHomeChannel | null
    archetypes: ChatterVersusArchetype[]
}

export interface ChatterHeadToHead {
    /** Side `a` is always the lower chatter id — the payload is param-order independent. */
    a: ChatterVersusSide
    b: ChatterVersusSide
    sharedStreams: number
    sharedCreators: number
}

const chatterVersusKeys = {
    all: ['chatter', 'head-to-head'] as const,
    pair: (a: number, b: number) => {
        // Normalize like the backend cache so (a,b) and (b,a) share one cache entry.
        const [lo, hi] = a < b ? [a, b] : [b, a]
        return [...chatterVersusKeys.all, { a: lo, b: hi }] as const
    },
}

const mapSide = (value: unknown, label: string): ChatterVersusSide => {
    const side = requireRecord(value, label)
    return {
        chatterId: requireFiniteNumberField(side, 'chatter_id', label),
        nick: requireStringField(side, 'nick', label),
        isBot: requireNullableBooleanField(side, 'is_bot', label),
        messages: requireFiniteNumberField(side, 'messages', label),
        streamsAttended: requireFiniteNumberField(side, 'streams_attended', label),
        creatorsVisited: requireFiniteNumberField(side, 'creators_visited', label),
        firstSeen: requireNullableStringField(side, 'first_seen', label),
        lastSeen: requireNullableStringField(side, 'last_seen', label),
        homeChannel: mapHomeChannel(side.home_channel, `${label}.home_channel`),
        archetypes: mapArchetypeBadges(side, label),
    }
}

export const mapChatterHeadToHead = (value: unknown): ChatterHeadToHead => {
    const data = requireRecord(value, 'chatter head-to-head')
    return {
        a: mapSide(data.a, 'chatter head-to-head.a'),
        b: mapSide(data.b, 'chatter head-to-head.b'),
        sharedStreams: requireFiniteNumberField(data, 'shared_streams', 'chatter head-to-head'),
        sharedCreators: requireFiniteNumberField(data, 'shared_creators', 'chatter head-to-head'),
    }
}

export const useChatterHeadToHead = (
    chatterA: number | null,
    chatterB: number | null,
) => useQuery({
    queryKey: chatterVersusKeys.pair(chatterA ?? 0, chatterB ?? 0),
    queryFn: async () => mapChatterHeadToHead(
        await retrieveChatterHeadToHead(chatterA as number, chatterB as number),
    ),
    enabled: Boolean(chatterA) && Boolean(chatterB) && chatterA !== chatterB,
})
