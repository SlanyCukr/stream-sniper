import type { ScenePulseRequest, SceneCopypastaRequest } from '@/lib/api/scene'

export type SceneCopypastaFilters = SceneCopypastaRequest & { pageIndex?: number, pageSize?: number }

interface RankingsFilters {
    window?: string
    limit?: number
    offset?: number
}

interface HighlightsFilters {
    window?: string
    creatorId?: number | null
    sort?: string
    limit?: number
    offset?: number
}

interface TrendingFilters {
    window?: number
    creatorId?: number | null
    limit?: number
}

interface SearchMessagesKeyFilters {
    q: string
    creatorId: number | null
    days: number | null
    limit: number
    offset: number
}

interface SearchFirstKeyFilters {
    q: string
    creatorId: number | null
}

interface SearchFrequencyKeyFilters {
    q: string
    days: number | null
    creatorId: number | null
}

interface SearchContextKeyFilters {
    streamId: number | null
    messageId: number | null
    radius: number | null
}

export const sceneKeys = {
    all: [
        'scene',
    ] as const,
    live: () => [
        ...sceneKeys.all,
        'live',
    ] as const,
    leaderboard: (windowDays: number) => [
        ...sceneKeys.all,
        'leaderboard',
        { windowDays },
    ] as const,
    copypastas: (filters: SceneCopypastaFilters) => [
        ...sceneKeys.all,
        'copypastas',
        filters,
    ] as const,
    copypasta: (messageTextId: number, contextSeconds: number) => [
        ...sceneKeys.all,
        'copypasta',
        { messageTextId, contextSeconds },
    ] as const,
    pulse: (filters: ScenePulseRequest) => [...sceneKeys.all, 'pulse', filters] as const,
    digest: (days: number) => [...sceneKeys.all, 'digest', { days }] as const,
    rankings: (filters: RankingsFilters) => [...sceneKeys.all, 'rankings', filters] as const,
    highlights: (filters: HighlightsFilters) => [...sceneKeys.all, 'highlights', filters] as const,
    trendingCopypastas: (filters: TrendingFilters) => [...sceneKeys.all, 'trending', 'copypastas', filters] as const,
    trendingEmotes: (filters: TrendingFilters) => [...sceneKeys.all, 'trending', 'emotes', filters] as const,
    wrapped: (days: number) => [...sceneKeys.all, 'wrapped', { days }] as const,
    radar: () => [...sceneKeys.all, 'radar'] as const,
    searchMessages: (filters: SearchMessagesKeyFilters) => [...sceneKeys.all, 'search', 'messages', filters] as const,
    searchFirst: (filters: SearchFirstKeyFilters) => [...sceneKeys.all, 'search', 'first', filters] as const,
    searchFrequency: (filters: SearchFrequencyKeyFilters) => [...sceneKeys.all, 'search', 'frequency', filters] as const,
    searchContext: (params: SearchContextKeyFilters) => [...sceneKeys.all, 'search', 'context', params] as const,
}
