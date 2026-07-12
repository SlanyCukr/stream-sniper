import { useQuery } from '@tanstack/react-query'
import {
    retrieveCreatorEmotes,
    retrieveStreamEmotes,
    retrieveStreamMentions,
    retrieveStreamPhrases,
} from '@/lib/api'

export const streamInsightsKeys = {
    all: ['stream-insights'],
    mentions: (streamId, limit) => [...streamInsightsKeys.all, 'mentions', { streamId, limit }],
    emotes: (streamId, limit) => [...streamInsightsKeys.all, 'emotes', { streamId, limit }],
    phrases: (streamId, limit) => [...streamInsightsKeys.all, 'phrases', { streamId, limit }],
    creatorEmotes: (creatorId, limit) => [...streamInsightsKeys.all, 'creator-emotes', { creatorId, limit }],
}

const mapEmote = e => ({
    name: e.name,
    source: e.source,
    providerId: e.provider_id,
    usageCount: e.usage_count,
    chatterCount: e.chatter_count,
    streamCount: e.stream_count,
})

export const useStreamMentions = (streamId, limit = 20, options = {}) => useQuery({
    queryKey: streamInsightsKeys.mentions(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamMentions(streamId, limit)
        const data = response.data || {}
        return {
            mentioned: (data.mentioned || []).map(m => ({
                chatterId: m.chatter_id,
                nick: m.nick,
                count: m.count,
            })),
            pairs: (data.pairs || []).map(p => ({
                fromChatterId: p.from_chatter_id,
                fromNick: p.from_nick,
                toChatterId: p.to_chatter_id,
                toNick: p.to_nick,
                count: p.count,
            })),
        }
    },
    enabled: Boolean(streamId),
    ...options,
})

export const useStreamEmotes = (streamId, limit = 25, options = {}) => useQuery({
    queryKey: streamInsightsKeys.emotes(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamEmotes(streamId, limit)
        return {
            emotes: (response.data?.emotes || []).map(mapEmote),
        }
    },
    enabled: Boolean(streamId),
    ...options,
})

export const useStreamPhrases = (streamId, limit = 25, options = {}) => useQuery({
    queryKey: streamInsightsKeys.phrases(streamId, limit),
    queryFn: async () => {
        const response = await retrieveStreamPhrases(streamId, limit)
        return {
            phrases: (response.data?.phrases || []).map(p => ({
                phrase: p.phrase,
                usageCount: p.usage_count,
                chatterCount: p.chatter_count,
            })),
        }
    },
    enabled: Boolean(streamId),
    ...options,
})

export const useCreatorEmotes = (creatorId, limit = 25, options = {}) => useQuery({
    queryKey: streamInsightsKeys.creatorEmotes(creatorId, limit),
    queryFn: async () => {
        const response = await retrieveCreatorEmotes(creatorId, limit)
        return {
            emotes: (response.data?.emotes || []).map(mapEmote),
        }
    },
    enabled: Boolean(creatorId),
    ...options,
})
