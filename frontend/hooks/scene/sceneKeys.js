/** @typedef {import('@/lib/api/scene').ScenePulseRequest} ScenePulseFilters */
/** @typedef {import('@/lib/api/scene').SceneCopypastaRequest & {pageIndex?: number, pageSize?: number}} SceneCopypastaFilters */

export const sceneKeys = {
    all: [
        'scene',
    ],
    live: () => [
        ...sceneKeys.all,
        'live',
    ],
    leaderboard: (/** @type {number} */ windowDays) => [
        ...sceneKeys.all,
        'leaderboard',
        { windowDays },
    ],
    copypastas: (/** @type {SceneCopypastaFilters} */ filters) => [
        ...sceneKeys.all,
        'copypastas',
        filters,
    ],
    copypasta: (/** @type {number} */ messageTextId, /** @type {number} */ contextSeconds) => [
        ...sceneKeys.all,
        'copypasta',
        { messageTextId, contextSeconds },
    ],
    pulse: (/** @type {ScenePulseFilters} */ filters) => [...sceneKeys.all, 'pulse', filters],
    digest: (/** @type {number} */ days) => [...sceneKeys.all, 'digest', { days }],
    rankings: (/** @type {object} */ filters) => [...sceneKeys.all, 'rankings', filters],
    highlights: (/** @type {object} */ filters) => [...sceneKeys.all, 'highlights', filters],
    trendingCopypastas: (/** @type {object} */ filters) => [...sceneKeys.all, 'trending', 'copypastas', filters],
    trendingEmotes: (/** @type {object} */ filters) => [...sceneKeys.all, 'trending', 'emotes', filters],
    searchMessages: (/** @type {object} */ filters) => [...sceneKeys.all, 'search', 'messages', filters],
    searchFirst: (/** @type {object} */ filters) => [...sceneKeys.all, 'search', 'first', filters],
    searchFrequency: (/** @type {object} */ filters) => [...sceneKeys.all, 'search', 'frequency', filters],
    searchContext: (/** @type {object} */ params) => [...sceneKeys.all, 'search', 'context', params],
}
