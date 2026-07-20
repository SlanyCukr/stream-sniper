import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
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

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

export interface SceneLiveChannel {
    creatorId: number
    nick: string
    displayName: string | null
    profileImageUrl: string | null
    viewerCount: number | null
    title: string | null
    sessionStartedAt: string | null
    sampledAt: string | null
}

export interface SceneLive {
    live: SceneLiveChannel[]
    liveCount: number
    lastSampleAt: string | null
}

const mapSceneLive = (value: unknown): SceneLive => {
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

export interface SceneLeaderboardEntry {
    rank: number
    creatorId: number
    nick: string
    displayName: string | null
    profileImageUrl: string | null
    streams: number
    hoursStreamed: number | null
    totalMessages: number
    msgsPerMin: number | null
    chatterAppearances: number
    peakViewers: number | null
}

export interface SceneLeaderboard {
    windowDays: number
    computedAt: string | null
    entries: SceneLeaderboardEntry[]
}

const mapSceneLeaderboard = (value: unknown): SceneLeaderboard => {
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

export const useSceneLive = (options: QueryOptions<SceneLive> = {}) => {
    const { enabled = true, refetchInterval = 30000, ...queryOptions } = options
    return useQuery({
        ...queryOptions,
        queryKey: sceneKeys.live(),
        queryFn: async () => mapSceneLive(await retrieveSceneLive()),
        enabled,
        refetchInterval,
    })
}

export const useSceneLeaderboard = (
    { windowDays = 7 }: { windowDays?: 7 | 30 } = {},
    { enabled = true, ...options }: QueryOptions<SceneLeaderboard> = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.leaderboard(windowDays),
    queryFn: async () => mapSceneLeaderboard(await retrieveSceneLeaderboard(windowDays)),
    enabled: Boolean(windowDays) && enabled,
})
