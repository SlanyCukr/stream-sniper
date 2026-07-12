import { useQuery } from '@tanstack/react-query'
import {
    retrieveSceneCopypastas,
    retrieveSceneLeaderboard,
    retrieveSceneLive,
} from '@/lib/api'

/**
 * Query key factory for scene-wide queries (live now, leaderboard, copypastas)
 */
export const sceneKeys = {
    all: [
        'scene',
    ],
    live: () => [
        ...sceneKeys.all,
        'live',
    ],
    leaderboard: windowDays => [
        ...sceneKeys.all,
        'leaderboard',
        { windowDays },
    ],
    copypastas: filters => [
        ...sceneKeys.all,
        'copypastas',
        filters,
    ],
}

/**
 * Custom hook for currently-live tracked streamers, mapped to camelCase.
 *
 * Liveness is inferred from viewer-sample freshness (samples only exist while
 * live), so `lastSampleAt` is surfaced for tracker-health: a stale value means
 * the tracker is down, not that nobody is live. Polls every 30s by default.
 *
 * Nullable = unknown contract: title/sessionStartedAt/profileImageUrl may be
 * null — preserved via `?? null`, never defaulted.
 *
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {live: [{creatorId, nick, displayName,
 *   profileImageUrl, viewerCount, title, sessionStartedAt, sampledAt}],
 *   liveCount, lastSampleAt}
 */
export const useSceneLive = (options = {}) => useQuery({
    queryKey: sceneKeys.live(),
    queryFn: async () => {
        const response = await retrieveSceneLive()
        const data = response.data || {
        }
        return {
            live: (data.live || []).map(s => ({
                creatorId: s.creator_id,
                nick: s.nick,
                displayName: s.display_name ?? null,
                profileImageUrl: s.profile_image_url ?? null,
                viewerCount: s.viewer_count ?? null,
                title: s.title ?? null,
                sessionStartedAt: s.session_started_at ?? null,
                sampledAt: s.sampled_at ?? null,
            })),
            liveCount: data.live_count ?? 0,
            lastSampleAt: data.last_sample_at ?? null,
        }
    },
    refetchInterval: 30000,
    ...options,
})

/**
 * Custom hook for the scene-wide creator leaderboard, mapped to camelCase.
 *
 * Nullable = unknown contract: hoursStreamed is null when no closed streams,
 * msgsPerMin is null when no rolled-up metrics exist in the window, and
 * peakViewers is null when the creator has no viewer samples — all preserved
 * via `?? null` and rendered as '--' (never 0).
 *
 * @param {7|30} windowDays - Leaderboard window in days
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {windowDays, computedAt,
 *   entries: [{rank, creatorId, nick, displayName, profileImageUrl, streams,
 *   hoursStreamed, totalMessages, msgsPerMin, chatterAppearances, peakViewers}]}
 */
export const useSceneLeaderboard = (windowDays, options = {}) => useQuery({
    queryKey: sceneKeys.leaderboard(windowDays),
    queryFn: async () => {
        const response = await retrieveSceneLeaderboard(windowDays)
        const data = response.data || {
        }
        return {
            windowDays: data.window_days,
            computedAt: data.computed_at ?? null,
            entries: (data.entries || []).map(e => ({
                rank: e.rank,
                creatorId: e.creator_id,
                nick: e.nick,
                displayName: e.display_name ?? null,
                profileImageUrl: e.profile_image_url ?? null,
                streams: e.streams,
                hoursStreamed: e.hours_streamed ?? null,
                totalMessages: e.total_messages,
                msgsPerMin: e.msgs_per_min ?? null,
                chatterAppearances: e.chatter_appearances,
                peakViewers: e.peak_viewers ?? null,
            })),
        }
    },
    enabled: Boolean(windowDays),
    ...options,
})

/**
 * Custom hook for the scene-wide copypasta library, mapped to camelCase.
 * Mirrors useMomentsQueue: filterable, offset-paginated (rows, total).
 *
 * @param {object} filters
 * @param {number} [filters.days] - Window in days (omitted = all-time)
 * @param {number} [filters.creatorId] - Restrict to one creator
 * @param {('usage'|'spread'|'recent')} [filters.sort] - Sort mode
 * @param {number} [filters.limit] - Page size
 * @param {number} [filters.offset] - Row offset
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {total, items: [{messageTextId,
 *   text, usageCount, chatterAppearances, streamCount, creatorCount,
 *   firstSeen, lastStreamStart}]}
 */
export const useSceneCopypastas = ({
    days, creatorId, sort, limit, offset,
} = {}, options = {}) => useQuery({
    queryKey: sceneKeys.copypastas({
        days, creatorId, sort, limit, offset,
    }),
    queryFn: async () => {
        const response = await retrieveSceneCopypastas({
            days, creatorId, sort, limit, offset,
        })
        const data = response.data || {
        }
        return {
            total: data.total ?? 0,
            items: (data.items || []).map(p => ({
                messageTextId: p.message_text_id,
                text: p.text,
                usageCount: p.usage_count,
                chatterAppearances: p.chatter_appearances,
                streamCount: p.stream_count,
                creatorCount: p.creator_count,
                firstSeen: p.first_seen ?? null,
                lastStreamStart: p.last_stream_start ?? null,
            })),
        }
    },
    ...options,
})
