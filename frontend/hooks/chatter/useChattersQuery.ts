import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveChatterStreamActivity } from '@/lib/api/chatter'
import {
    requireArray,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

type QueryOptions<T> = Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, 'queryKey' | 'queryFn'>

export interface ChatterStreamActivity {
    streamId: number
    streamTitle: string
    start: string
    creatorId: number
    creatorDisplayName: string
    messageCount: number
    isBot: boolean | null
}

const mapChatterActivity = (value: unknown, index = 0): ChatterStreamActivity => {
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
    ] as const,
    streamActivity: (chatterId: number) => [
        ...chattersKeys.all,
        'stream-activity',
        chatterId,
    ] as const,
}

export const useChatterStreamActivity = (
    chatterId: number,
    { enabled = true, ...options }: QueryOptions<ChatterStreamActivity[]> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: chattersKeys.streamActivity(chatterId),
    queryFn: async () => {
        const response = await retrieveChatterStreamActivity(chatterId)
        return requireArray(response.data, 'chatter stream activity').map((value, index) => mapChatterActivity(value, index))
    },
    enabled: Boolean(chatterId) && enabled,
})
