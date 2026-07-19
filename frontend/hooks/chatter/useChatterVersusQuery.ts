import { useQuery } from '@tanstack/react-query'
import { retrieveChatterHeadToHead } from '@/lib/api/chatter'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

export interface ChatterVersusHomeChannel {
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    messages: number
    /** messages / side total, rounded server-side to 4 places. */
    share: number
}

export interface ChatterVersusArchetype {
    key: string
    label: string
    description: string
}

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
    const homeChannel = side.home_channel === null || side.home_channel === undefined
        ? null
        : requireRecord(side.home_channel, `${label}.home_channel`)
    return {
        chatterId: requireFiniteNumberField(side, 'chatter_id', label),
        nick: requireStringField(side, 'nick', label),
        isBot: requireNullableBooleanField(side, 'is_bot', label),
        messages: requireFiniteNumberField(side, 'messages', label),
        streamsAttended: requireFiniteNumberField(side, 'streams_attended', label),
        creatorsVisited: requireFiniteNumberField(side, 'creators_visited', label),
        firstSeen: requireNullableStringField(side, 'first_seen', label),
        lastSeen: requireNullableStringField(side, 'last_seen', label),
        homeChannel: homeChannel === null ? null : {
            creatorId: requireFiniteNumberField(homeChannel, 'creator_id', `${label}.home_channel`),
            creatorNick: requireStringField(homeChannel, 'creator_nick', `${label}.home_channel`),
            creatorDisplayName: requireStringField(homeChannel, 'creator_display_name', `${label}.home_channel`),
            messages: requireFiniteNumberField(homeChannel, 'messages', `${label}.home_channel`),
            share: requireFiniteNumberField(homeChannel, 'share', `${label}.home_channel`),
        },
        archetypes: requireArrayField(side, 'archetypes', label).map((entry, index) => {
            const badgeLabel = `${label}.archetypes[${index}]`
            const badge = requireRecord(entry, badgeLabel)
            return {
                key: requireStringField(badge, 'key', badgeLabel),
                label: requireStringField(badge, 'label', badgeLabel),
                description: requireStringField(badge, 'description', badgeLabel),
            }
        }),
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
    queryKey: chatterA && chatterB
        ? chatterVersusKeys.pair(chatterA, chatterB)
        : [...chatterVersusKeys.all, { a: chatterA, b: chatterB }],
    queryFn: async () => mapChatterHeadToHead(
        (await retrieveChatterHeadToHead(chatterA as number, chatterB as number)).data,
    ),
    enabled: Boolean(chatterA) && Boolean(chatterB) && chatterA !== chatterB,
})
