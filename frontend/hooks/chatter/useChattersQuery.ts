import { retrieveChatterStreamActivity } from '@/lib/api/chatter'
import {
    requireArray,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'

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

const mapChatterStreamActivities = (value: unknown): ChatterStreamActivity[] => (
    requireArray(value, 'chatter stream activity').map((item, index) => mapChatterActivity(item, index))
)

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

const chatterStreamActivityQuery = defineGatedQuery({
    label: 'chatter stream activity',
    key: (chatterId: number) => chattersKeys.streamActivity(chatterId),
    validate: chatterId => (chatterId ? chatterId : null),
    fetch: chatterId => retrieveChatterStreamActivity(chatterId),
    map: mapChatterStreamActivities,
})

export const useChatterStreamActivity = (
    chatterId: number,
    options: QueryOptions<ChatterStreamActivity[]> = {},
) => chatterStreamActivityQuery(chatterId, options)
