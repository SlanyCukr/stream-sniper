import { useQuery } from '@tanstack/react-query'
import { retrieveSceneLeaderboard, retrieveSceneLive } from '@/lib/api/scene'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

/** @param {unknown} value */
const mapSceneLive = value => {
    const data = requireRecord(value, 'scene live')
    return {
        live: requireArrayField(data, 'live', 'scene live').map((value, index) => {
            const label = `scene live.live[${index}]`
            const stream = requireRecord(value, label)
            return {
                creatorId: requireFiniteNumberField(stream, 'creator_id', label),
                nick: requireStringField(stream, 'nick', label),
                displayName: requireNullableStringField(stream, 'display_name', label),
                profileImageUrl: requireNullableStringField(stream, 'profile_image_url', label),
                viewerCount: requireNullableFiniteNumberField(stream, 'viewer_count', label),
                title: requireNullableStringField(stream, 'title', label),
                sessionStartedAt: requireNullableStringField(stream, 'session_started_at', label),
                sampledAt: requireNullableStringField(stream, 'sampled_at', label),
            }
        }),
        liveCount: requireFiniteNumberField(data, 'live_count', 'scene live'),
        lastSampleAt: requireNullableStringField(data, 'last_sample_at', 'scene live'),
    }
}

/** @param {unknown} value */
const mapSceneLeaderboard = value => {
    const data = requireRecord(value, 'scene leaderboard')
    return {
        windowDays: requireFiniteNumberField(data, 'window_days', 'scene leaderboard'),
        computedAt: requireNullableStringField(data, 'computed_at', 'scene leaderboard'),
        entries: requireArrayField(data, 'entries', 'scene leaderboard').map((value, index) => {
            const label = `scene leaderboard.entries[${index}]`
            const entry = requireRecord(value, label)
            return {
                rank: requireFiniteNumberField(entry, 'rank', label),
                creatorId: requireFiniteNumberField(entry, 'creator_id', label),
                nick: requireStringField(entry, 'nick', label),
                displayName: requireNullableStringField(entry, 'display_name', label),
                profileImageUrl: requireNullableStringField(entry, 'profile_image_url', label),
                streams: requireFiniteNumberField(entry, 'streams', label),
                hoursStreamed: requireNullableFiniteNumberField(entry, 'hours_streamed', label),
                totalMessages: requireFiniteNumberField(entry, 'total_messages', label),
                msgsPerMin: requireNullableFiniteNumberField(entry, 'msgs_per_min', label),
                chatterAppearances: requireFiniteNumberField(entry, 'chatter_appearances', label),
                peakViewers: requireNullableFiniteNumberField(entry, 'peak_viewers', label),
            }
        }),
    }
}

/** @param {QueryOptions} [options] */
export const useSceneLive = (options = {}) => {
    const { enabled = true, refetchInterval = 30000, ...queryOptions } = options
    return useQuery({
        ...queryOptions,
        queryKey: sceneKeys.live(),
        queryFn: async () => mapSceneLive((await retrieveSceneLive()).data),
        enabled,
        refetchInterval,
    })
}

/** @param {{windowDays?:7|30}} [params] @param {QueryOptions} [options] */
export const useSceneLeaderboard = ({ windowDays = 7 } = {}, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: sceneKeys.leaderboard(windowDays),
    queryFn: async () => mapSceneLeaderboard((await retrieveSceneLeaderboard(windowDays)).data),
    enabled: Boolean(windowDays) && enabled,
})
