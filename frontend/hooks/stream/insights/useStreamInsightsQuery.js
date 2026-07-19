import { useQuery } from '@tanstack/react-query'
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

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */
/** @typedef {{limit?:number}} InsightParams */

const streamInsightsKeys = {
    all: ['stream-insights'],
    mentions: (/** @type {number} */ streamId, /** @type {number} */ limit) => [...streamInsightsKeys.all, 'mentions', { streamId, limit }],
    emotes: (/** @type {number} */ streamId, /** @type {number} */ limit) => [...streamInsightsKeys.all, 'emotes', { streamId, limit }],
    phrases: (/** @type {number} */ streamId, /** @type {number} */ limit) => [...streamInsightsKeys.all, 'phrases', { streamId, limit }],
    creatorEmotes: (/** @type {number} */ creatorId, /** @type {number} */ limit) => [...streamInsightsKeys.all, 'creator-emotes', { creatorId, limit }],
}

/**
 * @param {unknown} value
 * @param {string} label
 */
const mapEmote = (value, label) => {
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

/** @param {unknown} value */
const mapStreamMentions = value => {
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

/** @param {unknown} value */
const mapStreamEmotes = value => {
    const data = requireRecord(value, 'stream emotes')
    return {
        emotes: requireArrayField(data, 'emotes', 'stream emotes')
            .map((emote, index) => mapEmote(emote, `stream emotes.emotes[${index}]`)),
    }
}

/** @param {unknown} value */
const mapStreamPhrases = value => {
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

/** @param {number} streamId @param {InsightParams} [params] @param {QueryOptions} [options] */
export const useStreamMentions = (streamId, { limit = 20 } = {}, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.mentions(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamMentions(streamId, limit)
        return mapStreamMentions(response.data)
    },
    enabled: Boolean(streamId) && enabled,
})

/** @param {number} streamId @param {InsightParams} [params] @param {QueryOptions} [options] */
export const useStreamEmotes = (streamId, { limit = 25 } = {}, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.emotes(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamEmotes(streamId, limit)
        return mapStreamEmotes(response.data)
    },
    enabled: Boolean(streamId) && enabled,
})

/** @param {number} streamId @param {InsightParams} [params] @param {QueryOptions} [options] */
export const useStreamPhrases = (streamId, { limit = 25 } = {}, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: streamInsightsKeys.phrases(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamPhrases(streamId, limit)
        return mapStreamPhrases(response.data)
    },
    enabled: Boolean(streamId) && enabled,
})

/** @param {number} creatorId @param {InsightParams} [params] @param {QueryOptions} [options] */
export const useCreatorEmotes = (creatorId, { limit = 25 } = {}, { enabled = true, ...options } = {}) => useQuery({
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
