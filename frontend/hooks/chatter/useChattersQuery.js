import { useQuery } from '@tanstack/react-query'
import { retrieveChatterStreamActivity } from '@/lib/api/chatter'
import {
    requireArray,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

/** @param {unknown} value @param {number} [index] */
const mapChatterActivity = (value, index = 0) => {
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
    streamActivity: (/** @type {number} */ chatterId) => [
        ...chattersKeys.all,
        'stream-activity',
        chatterId,
    ],
}

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
