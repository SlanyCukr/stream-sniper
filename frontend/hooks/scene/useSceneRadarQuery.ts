import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveSceneRadar } from '@/lib/api/scene'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/** One trailing per-minute bucket in a channel's velocity trace (ascending, zero-filled). */
export interface RadarMinute {
    minute: string
    messages: number
}

/** One live channel's near-real-time chat velocity row. */
export interface RadarChannel {
    streamId: number
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    profileImageUrl: string | null
    streamTitle: string | null
    startedAt: string | null
    messagesLastMinute: number
    uniqueChattersLastMinute: number
    baselinePerMinute: number | null
    ratio: number | null
    spiking: boolean
    minutes: RadarMinute[]
}

/** Camel-cased view model for `GET /scene/radar`. */
export interface SceneRadar {
    generatedAt: string
    channels: RadarChannel[]
}

/** Validate the radar envelope at the boundary, then project the view model. */
export const mapSceneRadar = (value: unknown): SceneRadar => {
    const root = requireRecord(value, 'scene radar')
    return {
        generatedAt: requireStringField(root, 'generated_at', 'scene radar'),
        channels: requireArrayField(root, 'channels', 'scene radar').map((raw, index) => {
            const label = `scene radar.channels[${index}]`
            const channel = requireRecord(raw, label)
            return {
                streamId: requireFiniteNumberField(channel, 'stream_id', label),
                creatorId: requireFiniteNumberField(channel, 'creator_id', label),
                creatorNick: requireStringField(channel, 'creator_nick', label),
                creatorDisplayName: requireStringField(channel, 'creator_display_name', label),
                profileImageUrl: requireNullableStringField(channel, 'profile_image_url', label),
                streamTitle: requireNullableStringField(channel, 'stream_title', label),
                startedAt: requireNullableStringField(channel, 'started_at', label),
                messagesLastMinute: requireFiniteNumberField(channel, 'messages_last_minute', label),
                uniqueChattersLastMinute: requireFiniteNumberField(channel, 'unique_chatters_last_minute', label),
                baselinePerMinute: requireNullableFiniteNumberField(channel, 'baseline_per_minute', label),
                ratio: requireNullableFiniteNumberField(channel, 'ratio', label),
                spiking: requireBooleanField(channel, 'spiking', label),
                minutes: requireArrayField(channel, 'minutes', label).map((rawMinute, minuteIndex) => {
                    const minuteLabel = `${label}.minutes[${minuteIndex}]`
                    const minute = requireRecord(rawMinute, minuteLabel)
                    return {
                        minute: requireStringField(minute, 'minute', minuteLabel),
                        messages: requireFiniteNumberField(minute, 'messages', minuteLabel),
                    }
                }),
            }
        }),
    }
}

type RadarQueryOptions = Omit<
    UseQueryOptions<SceneRadar, Error, SceneRadar, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean, refetchInterval?: number }

/**
 * Poll the live moment radar. Mirrors `useSceneLive`'s polling contract exactly:
 * `refetchInterval` defaults to 30s and `enabled` is a passthrough, so React
 * Query pauses fetching while the window/tab is hidden and resumes on focus. A
 * failed poll after data exists keeps the last successful payload (RQ default),
 * so the grid never blanks mid-session.
 */
export const useSceneRadar = (options: RadarQueryOptions = {}) => {
    const { enabled = true, refetchInterval = 30000, ...queryOptions } = options
    return useQuery({
        ...queryOptions,
        queryKey: sceneKeys.radar(),
        queryFn: async () => mapSceneRadar(await retrieveSceneRadar()),
        enabled,
        refetchInterval,
    })
}
