import type { SceneCopypastaRequest } from '@/lib/models/sceneFilters'

export const COPYPASTA_SORT_OPTIONS = [
    { value: 'usage', label: 'Most used' },
    { value: 'spread', label: 'Widest spread' },
    { value: 'recent', label: 'Recent' },
] as const satisfies ReadonlyArray<{
    value: NonNullable<SceneCopypastaRequest['sort']>
    label: string
}>
