import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveStreamEmotes,
    retrieveStreamMentions,
    retrieveStreamPhrases,
} from '@/lib/api/streams'
import { retrieveCreatorEmotes } from '@/lib/api/creators'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

interface InsightParams {
    limit?: number
}

export interface StreamEmote {
    name: string
    source: string
    providerId: string | null
    usageCount: number
    chatterCount: number
    streamCount?: number
}

export interface StreamMention {
    chatterId: number
    nick: string
    count: number
}

export interface StreamMentionPair {
    fromChatterId: number
    fromNick: string
    toChatterId: number
    toNick: string
    count: number
}

export interface StreamMentions {
    mentioned: StreamMention[]
    pairs: StreamMentionPair[]
}

export interface StreamEmotes {
    emotes: StreamEmote[]
}

export interface StreamPhrase {
    phrase: string
    usageCount: number
    chatterCount: number
}

export interface StreamPhrases {
    phrases: StreamPhrase[]
}

export interface CreatorEmotes {
    emotes: StreamEmote[]
}

const streamInsightsKeys = {
    all: ['stream-insights'],
    mentions: (streamId: number, limit: number) => [...streamInsightsKeys.all, 'mentions', { streamId, limit }],
    emotes: (streamId: number, limit: number) => [...streamInsightsKeys.all, 'emotes', { streamId, limit }],
    phrases: (streamId: number, limit: number) => [...streamInsightsKeys.all, 'phrases', { streamId, limit }],
    creatorEmotes: (creatorId: number, limit: number) => [...streamInsightsKeys.all, 'creator-emotes', { creatorId, limit }],
}

const mapEmote = (value: unknown, label: string): StreamEmote => {
    const emote = requireRecord(value, label)
    return {
        name: requireStringField(emote, 'name', label),
        source: requireStringField(emote, 'source', label),
        providerId: requireNullableStringField(emote, 'provider_id', label),
        usageCount: requireFiniteNumberField(emote, 'usage_count', label),
        chatterCount: requireFiniteNumberField(emote, 'chatter_count', label),
        streamCount: emote.stream_count === undefined
            ? undefined
            : requireFiniteNumberField(emote, 'stream_count', label),
    }
}

const mapStreamMentions = (value: unknown): StreamMentions => {
    const data = requireRecord(value, 'stream mentions')
    return {
        mentioned: requireArrayField(data, 'mentioned', 'stream mentions').map((value, index) => {
            const label = `stream mentions.mentioned[${index}]`
            const mention = requireRecord(value, label)
            return {
                chatterId: requireFiniteNumberField(mention, 'chatter_id', label),
                nick: requireStringField(mention, 'nick', label),
                count: requireFiniteNumberField(mention, 'count', label),
            }
        }),
        pairs: requireArrayField(data, 'pairs', 'stream mentions').map((value, index) => {
            const label = `stream mentions.pairs[${index}]`
            const pair = requireRecord(value, label)
            return {
                fromChatterId: requireFiniteNumberField(pair, 'from_chatter_id', label),
                fromNick: requireStringField(pair, 'from_nick', label),
                toChatterId: requireFiniteNumberField(pair, 'to_chatter_id', label),
                toNick: requireStringField(pair, 'to_nick', label),
                count: requireFiniteNumberField(pair, 'count', label),
            }
        }),
    }
}

const mapStreamEmotes = (value: unknown): StreamEmotes => {
    const data = requireRecord(value, 'stream emotes')
    return {
        emotes: requireArrayField(data, 'emotes', 'stream emotes')
            .map((emote, index) => mapEmote(emote, `stream emotes.emotes[${index}]`)),
    }
}

const mapStreamPhrases = (value: unknown): StreamPhrases => {
    const data = requireRecord(value, 'stream phrases')
    return {
        phrases: requireArrayField(data, 'phrases', 'stream phrases').map((value, index) => {
            const label = `stream phrases.phrases[${index}]`
            const phrase = requireRecord(value, label)
            return {
                phrase: requireStringField(phrase, 'phrase', label),
                usageCount: requireFiniteNumberField(phrase, 'usage_count', label),
                chatterCount: requireFiniteNumberField(phrase, 'chatter_count', label),
            }
        }),
    }
}

export const useStreamMentions = (
    streamId: number,
    { limit = 20 }: InsightParams = {},
    { enabled = true, ...options }: QueryOptions<StreamMentions> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.mentions(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamMentions(streamId, limit)
        return mapStreamMentions(response.data)
    },
    enabled: Boolean(streamId) && enabled,
})

export const useStreamEmotes = (
    streamId: number,
    { limit = 25 }: InsightParams = {},
    { enabled = true, ...options }: QueryOptions<StreamEmotes> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.emotes(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamEmotes(streamId, limit)
        return mapStreamEmotes(response.data)
    },
    enabled: Boolean(streamId) && enabled,
})

export const useStreamPhrases = (
    streamId: number,
    { limit = 25 }: InsightParams = {},
    { enabled = true, ...options }: QueryOptions<StreamPhrases> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.phrases(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamPhrases(streamId, limit)
        return mapStreamPhrases(response.data)
    },
    enabled: Boolean(streamId) && enabled,
})

export const useCreatorEmotes = (
    creatorId: number,
    { limit = 25 }: InsightParams = {},
    { enabled = true, ...options }: QueryOptions<CreatorEmotes> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.creatorEmotes(creatorId, limit),
    queryFn: async () => {
        const response = await retrieveCreatorEmotes(creatorId, limit)
        const data = requireRecord(response.data, 'creator emotes')
        return {
            emotes: requireArrayField(data, 'emotes', 'creator emotes')
                .map((emote, index) => mapEmote(emote, `creator emotes.emotes[${index}]`)),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
