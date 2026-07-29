import {
    retrieveStreamEmotes,
    retrieveStreamMentions,
    retrieveStreamPhrases,
} from '@/lib/api/streams'
import { retrieveCreatorEmotes } from '@/lib/api/creators'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

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

const mapCreatorEmotes = (value: unknown): CreatorEmotes => {
    const data = requireRecord(value, 'creator emotes')
    return {
        emotes: requireArrayField(data, 'emotes', 'creator emotes')
            .map((emote, index) => mapEmote(emote, `creator emotes.emotes[${index}]`)),
    }
}

const streamMentionsQuery = defineGatedQuery({
    label: 'stream mentions',
    key: ({ streamId, limit }: { streamId: number, limit: number }) => streamInsightsKeys.mentions(streamId, limit),
    validate: args => (args.streamId ? args : null),
    fetch: ({ streamId, limit }) => retrieveStreamMentions(streamId, limit),
    map: mapStreamMentions,
})

export const useStreamMentions = (
    streamId: number,
    { limit = 20 }: InsightParams = {},
    options: QueryOptions<StreamMentions> = {},
) => streamMentionsQuery({ streamId, limit }, options)

const streamEmotesQuery = defineGatedQuery({
    label: 'stream emotes',
    key: ({ streamId, limit }: { streamId: number, limit: number }) => streamInsightsKeys.emotes(streamId, limit),
    validate: args => (args.streamId ? args : null),
    fetch: ({ streamId, limit }) => retrieveStreamEmotes(streamId, limit),
    map: mapStreamEmotes,
})

export const useStreamEmotes = (
    streamId: number,
    { limit = 25 }: InsightParams = {},
    options: QueryOptions<StreamEmotes> = {},
) => streamEmotesQuery({ streamId, limit }, options)

const streamPhrasesQuery = defineGatedQuery({
    label: 'stream phrases',
    key: ({ streamId, limit }: { streamId: number, limit: number }) => streamInsightsKeys.phrases(streamId, limit),
    validate: args => (args.streamId ? args : null),
    fetch: ({ streamId, limit }) => retrieveStreamPhrases(streamId, limit),
    map: mapStreamPhrases,
})

export const useStreamPhrases = (
    streamId: number,
    { limit = 25 }: InsightParams = {},
    options: QueryOptions<StreamPhrases> = {},
) => streamPhrasesQuery({ streamId, limit }, options)

const creatorEmotesQuery = defineGatedQuery({
    label: 'creator emotes',
    key: ({ creatorId, limit }: { creatorId: number, limit: number }) => streamInsightsKeys.creatorEmotes(creatorId, limit),
    validate: args => (args.creatorId ? args : null),
    fetch: ({ creatorId, limit }) => retrieveCreatorEmotes(creatorId, limit),
    map: mapCreatorEmotes,
})

export const useCreatorEmotes = (
    creatorId: number,
    { limit = 25 }: InsightParams = {},
    options: QueryOptions<CreatorEmotes> = {},
) => creatorEmotesQuery({ creatorId, limit }, options)
