import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
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

export interface PassportDebut {
    streamId: number
    streamTitle: string
    creatorDisplayName: string
    time: string
}

export interface PassportHomeChannel {
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    messages: number
    share: number
}

export interface PassportLoyaltyRow {
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    messages: number
    streamsAttended: number
    share: number
}

export interface PassportMostActiveStream {
    streamId: number
    title: string
    creatorDisplayName: string
    messages: number
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
}

/**
 * Render a fractional share (0..1) as a single-decimal percentage string.
 * Pure so the passport card and its tests share one formatting rule.
 */
export const formatSharePct = (share: number): string => `${(share * 100).toFixed(1)}%`

/** Bar width (2..100) for a fractional share, clamped so tiny shares stay visible. */
export const shareBarWidth = (share: number): number => (
    Math.min(100, Math.max(2, Math.round(share * 100)))
)

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

const mapHomeChannel = (raw: unknown): PassportHomeChannel | null => {
    if (raw === null) return null
    const label = 'chatter passport.home_channel'
    const home = requireRecord(raw, label)
    return {
        creatorId: requireFiniteNumberField(home, 'creator_id', label),
        creatorNick: requireStringField(home, 'creator_nick', label),
        creatorDisplayName: requireStringField(home, 'creator_display_name', label),
        messages: requireFiniteNumberField(home, 'messages', label),
        share: requireFiniteNumberField(home, 'share', label),
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
        homeChannel: mapHomeChannel(root.home_channel),
        loyalty: requireArrayField(root, 'loyalty', 'chatter passport').map(mapLoyaltyRow),
        milestones: {
            mostActiveStream: mapMostActiveStream(milestones.most_active_stream),
        },
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
        return mapChatterPassport(response.data)
    },
    enabled: Number.isInteger(chatterId) && chatterId > 0 && enabled,
})
