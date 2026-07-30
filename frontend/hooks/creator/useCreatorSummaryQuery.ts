import { retrieveCreatorSummary } from '@/lib/api/creators'
import {
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'
import { creatorKeys } from './creatorKeys'

export interface CreatorSummaryLatestStream {
    streamId: number
    title: string
    start: string | null
}

export interface CreatorSummary {
    creatorId: number
    nick: string
    displayName: string
    profileImageUrl: string | null
    twitchUserId: string | null
    totalStreams: number
    firstStreamAt: string | null
    lastStreamAt: string | null
    totalMessages: number
    durationSeconds: number | null
    messagesPerMinute: number | null
    audienceSize: number
    regulars: number
    latestStream: CreatorSummaryLatestStream | null
}

const mapCreatorSummary = (value: unknown): CreatorSummary => {
    const data = requireRecord(value, 'creator summary')
    const latestStream = data.latest_stream === null
        ? null
        : (() => {
            const stream = requireRecord(data.latest_stream, 'creator summary.latest_stream')
            return {
                streamId: requireFiniteNumberField(stream, 'stream_id', 'creator summary.latest_stream'),
                title: requireStringField(stream, 'title', 'creator summary.latest_stream'),
                start: requireNullableStringField(stream, 'start', 'creator summary.latest_stream'),
            }
        })()
    return {
        creatorId: requireFiniteNumberField(data, 'creator_id', 'creator summary'),
        nick: requireStringField(data, 'nick', 'creator summary'),
        displayName: requireStringField(data, 'display_name', 'creator summary'),
        profileImageUrl: requireNullableStringField(data, 'profile_image_url', 'creator summary'),
        twitchUserId: requireNullableStringField(data, 'twitch_id', 'creator summary'),
        totalStreams: requireFiniteNumberField(data, 'total_streams', 'creator summary'),
        firstStreamAt: requireNullableStringField(data, 'first_stream_at', 'creator summary'),
        lastStreamAt: requireNullableStringField(data, 'last_stream_at', 'creator summary'),
        totalMessages: requireFiniteNumberField(data, 'total_messages', 'creator summary'),
        durationSeconds: requireNullableFiniteNumberField(data, 'duration_seconds', 'creator summary'),
        messagesPerMinute: requireNullableFiniteNumberField(data, 'messages_per_minute', 'creator summary'),
        audienceSize: requireFiniteNumberField(data, 'audience_size', 'creator summary'),
        regulars: requireFiniteNumberField(data, 'regulars', 'creator summary'),
        latestStream,
    }
}

const creatorSummaryQuery = defineGatedQuery({
    label: 'creator summary',
    key: (creatorId: number) => creatorKeys.summary(creatorId),
    validate: creatorId => (creatorId ? creatorId : null),
    fetch: retrieveCreatorSummary,
    map: mapCreatorSummary,
})

export const useCreatorSummary = (
    creatorId: number,
    options: QueryOptions<CreatorSummary> = {},
) => creatorSummaryQuery(creatorId, options)
