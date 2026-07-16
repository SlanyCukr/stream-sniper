import { api, buildQuery } from './client'

export interface OverlapCreatorDto {
  creator_id: number
  nick: string
  display_name: string
  chatters: number
  regulars: number
}

export interface OverlapPairDto {
  a: number
  b: number
  shared_chatters: number
  shared_regulars: number
  jaccard_chatters: number | null
  jaccard_regulars: number | null
}

export interface CommunityOverlapDto {
  creators: OverlapCreatorDto[]
  pairs: OverlapPairDto[]
  computed_at: string | null
}

export interface CreatorNeighborDto {
  creator_id: number
  nick: string
  display_name: string
  shared_chatters: number
  shared_regulars: number
}

export interface CreatorNeighborsDto {
  creator_id: number
  metric: 'regulars' | 'chatters'
  neighbors: CreatorNeighborDto[]
}

export const retrieveCommunityOverlap = (limit = 40) =>
  api.get<CommunityOverlapDto>(`/community/overlap?${buildQuery({ limit })}`)

export const retrieveCreatorNeighbors = (
  creatorId: number,
  request: { metric?: 'regulars' | 'chatters', limit?: number } = {},
) => api.get<CreatorNeighborsDto>(`/community/creators/${creatorId}/neighbors?${buildQuery({
  metric: request.metric,
  limit: request.limit,
})}`)
