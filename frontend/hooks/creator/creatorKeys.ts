interface CreatorRegularsFilters {
    minStreams?: number
    sort?: string
    dir?: 'asc' | 'desc'
    limit?: number
}

export const creatorKeys = {
    all: ['creator'] as const,
    catalog: () => [...creatorKeys.all, 'catalog', 'list'] as const,
    summary: (creatorId: number) => [...creatorKeys.all, 'summary', { creatorId }] as const,
    regulars: (creatorId: number, filters: CreatorRegularsFilters) => (
        [...creatorKeys.all, 'regulars', { creatorId, ...filters }] as const
    ),
    trends: (creatorId: number) => [...creatorKeys.all, 'trends', { creatorId }] as const,
    wrapped: (creatorId: number, days: number) => (
        [...creatorKeys.all, 'wrapped', { creatorId, days }] as const
    ),
    audienceMovement: (creatorId: number | null, days: number) => (
        [...creatorKeys.all, 'audience-movement', { creatorId, days }] as const
    ),
}
