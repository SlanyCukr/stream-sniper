import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { shareBarWidth } from '@/utils/numberUtils'
import { retrieveChatterPassport } from '@/lib/api/chatter'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { chattersKeys } from './useChattersQuery'
import { mapArchetypeBadges, mapHomeChannel, type ChatterHomeChannel } from './wireShapes'

interface PassportDebut {
    streamId: number
    streamTitle: string
    creatorDisplayName: string
    time: string
}

type PassportHomeChannel = ChatterHomeChannel

interface PassportLoyaltyRow {
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    messages: number
    streamsAttended: number
    share: number
}

interface PassportMostActiveStream {
    streamId: number
    title: string
    creatorDisplayName: string
    messages: number
}

interface PassportCompanion {
    chatterId: number
    nick: string
    sharedStreams: number
}

export interface ChatterPassport {
    chatter: {
        id: number
        nick: string
        isBot: boolean | null
        botReason: string | null
    }
    totals: {
        messages: number
        streamsAttended: number
        creatorsVisited: number
        firstSeen: string | null
        lastSeen: string | null
    }
    debut: PassportDebut | null
    homeChannel: PassportHomeChannel | null
    loyalty: PassportLoyaltyRow[]
    milestones: {
        mostActiveStream: PassportMostActiveStream | null
    }
    archetypes: Array<{ key: string, label: string, description: string }>
    companions: PassportCompanion[]
}

// Re-exported so existing passport imports/tests are unaffected by the
// numberUtils consolidation (same pattern as shareBarWidth below).
export { formatSharePct } from '@/utils/numberUtils'

/**
 * Bar width (2..100) for a fractional share, clamped so tiny shares stay
 * visible. Re-exported here so existing passport imports/tests are unaffected
 * by the numberUtils consolidation.
 */
export { shareBarWidth }

const mapDebut = (raw: unknown): PassportDebut | null => {
    if (raw === null) return null
    const label = 'chatter passport.debut'
    const debut = requireRecord(raw, label)
    return {
        streamId: requireFiniteNumberField(debut, 'stream_id', label),
        streamTitle: requireStringField(debut, 'stream_title', label),
        creatorDisplayName: requireStringField(debut, 'creator_display_name', label),
        time: requireStringField(debut, 'time', label),
    }
}

const mapLoyaltyRow = (raw: unknown, index: number): PassportLoyaltyRow => {
    const label = `chatter passport.loyalty[${index}]`
    const row = requireRecord(raw, label)
    return {
        creatorId: requireFiniteNumberField(row, 'creator_id', label),
        creatorNick: requireStringField(row, 'creator_nick', label),
        creatorDisplayName: requireStringField(row, 'creator_display_name', label),
        messages: requireFiniteNumberField(row, 'messages', label),
        streamsAttended: requireFiniteNumberField(row, 'streams_attended', label),
        share: requireFiniteNumberField(row, 'share', label),
    }
}

const mapCompanion = (raw: unknown, index: number): PassportCompanion => {
    const label = `chatter passport.companions[${index}]`
    const companion = requireRecord(raw, label)
    return {
        chatterId: requireFiniteNumberField(companion, 'chatter_id', label),
        nick: requireStringField(companion, 'nick', label),
        sharedStreams: requireFiniteNumberField(companion, 'shared_streams', label),
    }
}

const mapMostActiveStream = (raw: unknown): PassportMostActiveStream | null => {
    if (raw === null) return null
    const label = 'chatter passport.milestones.most_active_stream'
    const stream = requireRecord(raw, label)
    return {
        streamId: requireFiniteNumberField(stream, 'stream_id', label),
        title: requireStringField(stream, 'title', label),
        creatorDisplayName: requireStringField(stream, 'creator_display_name', label),
        messages: requireFiniteNumberField(stream, 'messages', label),
    }
}

export const mapChatterPassport = (value: unknown): ChatterPassport => {
    const root = requireRecord(value, 'chatter passport')
    const chatter = requireRecord(root.chatter, 'chatter passport.chatter')
    const totals = requireRecord(root.totals, 'chatter passport.totals')
    const milestones = requireRecord(root.milestones, 'chatter passport.milestones')

    return {
        chatter: {
            id: requireFiniteNumberField(chatter, 'id', 'chatter passport.chatter'),
            nick: requireStringField(chatter, 'nick', 'chatter passport.chatter'),
            isBot: requireNullableBooleanField(chatter, 'is_bot', 'chatter passport.chatter'),
            botReason: requireNullableStringField(chatter, 'bot_reason', 'chatter passport.chatter'),
        },
        totals: {
            messages: requireFiniteNumberField(totals, 'messages', 'chatter passport.totals'),
            streamsAttended: requireFiniteNumberField(totals, 'streams_attended', 'chatter passport.totals'),
            creatorsVisited: requireFiniteNumberField(totals, 'creators_visited', 'chatter passport.totals'),
            firstSeen: requireNullableStringField(totals, 'first_seen', 'chatter passport.totals'),
            lastSeen: requireNullableStringField(totals, 'last_seen', 'chatter passport.totals'),
        },
        debut: mapDebut(root.debut),
        homeChannel: mapHomeChannel(root.home_channel, 'chatter passport.home_channel'),
        loyalty: requireArrayField(root, 'loyalty', 'chatter passport').map(mapLoyaltyRow),
        milestones: {
            mostActiveStream: mapMostActiveStream(milestones.most_active_stream),
        },
        archetypes: mapArchetypeBadges(root, 'chatter passport'),
        companions: requireArrayField(root, 'companions', 'chatter passport').map(mapCompanion),
    }
}

export const chatterPassportKeys = {
    passport: (chatterId: number) => [
        ...chattersKeys.all,
        'passport',
        chatterId,
    ] as const,
}

type PassportQueryOptions = Omit<
    UseQueryOptions<ChatterPassport, Error, ChatterPassport, ReturnType<typeof chatterPassportKeys.passport>>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

export const useChatterPassport = (
    chatterId: number,
    { enabled = true, ...options }: PassportQueryOptions = {},
) => useQuery({
    ...options,
    queryKey: chatterPassportKeys.passport(chatterId),
    queryFn: async () => {
        const response = await retrieveChatterPassport(chatterId)
        return mapChatterPassport(response)
    },
    enabled: Number.isInteger(chatterId) && chatterId > 0 && enabled,
})
