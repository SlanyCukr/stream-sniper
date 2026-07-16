import { useQuery } from '@tanstack/react-query'
import {
    retrieveChattersOnStream,
    retrieveChatterIdentity,
    retrieveChatterStreamActivity,
} from '@/lib/api/chatter'
import {
    requireArray,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

/** @param {unknown} value @param {number} [index] */
export const mapChatterRow = (value, index = 0) => {
    const chatter = requireRecord(value, `stream chatters[${index}]`)
    return {
        chatterId: requireFiniteNumberField(chatter, 'chatter_id', `stream chatters[${index}]`),
        nick: requireStringField(chatter, 'nick', `stream chatters[${index}]`),
    }
}

/** @param {unknown} value @param {number} [index] */
export const mapChatterActivity = (value, index = 0) => {
    const activity = requireRecord(value, `chatter stream activity[${index}]`)
    const label = `chatter stream activity[${index}]`
    return {
        streamId: requireFiniteNumberField(activity, 'stream_id', label),
        streamTitle: requireStringField(activity, 'stream_title', label),
        start: requireStringField(activity, 'start', label),
        creatorId: requireFiniteNumberField(activity, 'creator_id', label),
        creatorDisplayName: requireStringField(activity, 'creator_display_name', label),
        messageCount: requireFiniteNumberField(activity, 'message_count', label),
        isBot: requireNullableBooleanField(activity, 'is_bot', label),
    }
}

export const chattersKeys = {
    all: [
        'chatters',
    ],
    list: (/** @type {number} */ streamId) => [
        ...chattersKeys.all,
        'list',
        { streamId },
    ],
    chatterId: (/** @type {string} */ nick) => [
        ...chattersKeys.all,
        'chatter-ids',
        nick,
    ],
    streamActivity: (/** @type {number} */ chatterId) => [
        ...chattersKeys.all,
        'stream-activity',
        chatterId,
    ],
}

/** @param {number} streamId @param {QueryOptions & {enabled?:boolean}} [options] */
export const useChatters = (streamId, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: chattersKeys.list(streamId),
    queryFn: async () => {
        const response = await retrieveChattersOnStream(streamId)
        return requireArray(response.data, 'stream chatters').map(mapChatterRow)
    },
    enabled: Boolean(streamId) && enabled,
})

/**
 * @param {string} nick
 * @param {QueryOptions & {enabled?:boolean}} [options]
 */
export const useChatterIdentity = (nick, { enabled = false, ...options } = {}) => useQuery({
    ...options,
    queryKey: chattersKeys.chatterId(nick),
    queryFn: async () => {
        const response = await retrieveChatterIdentity(nick)
        const data = requireRecord(response.data, 'chatter identity')
        return {
            chatterId: requireFiniteNumberField(data, 'chatter_id', 'chatter identity'),
            isBot: requireNullableBooleanField(data, 'is_bot', 'chatter identity'),
        }
    },
    enabled: Boolean(nick) && enabled,
})

/** @param {number} chatterId @param {QueryOptions & {enabled?:boolean}} [options] */
export const useChatterStreamActivity = (chatterId, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: chattersKeys.streamActivity(chatterId),
    queryFn: async () => {
        const response = await retrieveChatterStreamActivity(chatterId)
        return requireArray(response.data, 'chatter stream activity').map(mapChatterActivity)
    },
    enabled: Boolean(chatterId) && enabled,
})
