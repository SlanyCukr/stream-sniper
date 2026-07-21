export type SceneCopypastaSort = 'usage' | 'spread' | 'recent'

export interface SceneCopypastaRequest {
    days?: number
    creatorId?: number
    sort?: SceneCopypastaSort
    pageSize?: number
    rowOffset?: number
}

export type RankingsWindow = 'all' | '7' | '30'
export type HighlightsWindow = 'all' | '7' | '30'
export type HighlightsSort = 'hype' | 'recent'
export type TrendingWindow = 7 | 14 | 30

export interface SceneTrendingRequest {
    window?: TrendingWindow
    creatorId?: number
    limit?: number
}
