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

export interface HeadToHeadCreatorDto {
  creator_id: number
  nick: string
  display_name: string
  chatters: number
  regulars: number
  shared_chatter_share: number | null
  shared_regular_share: number | null
}

export interface CreatorHeadToHeadDto {
  /** Side `a` is always the lower creator id — the payload is param-order independent. */
  a: HeadToHeadCreatorDto
  b: HeadToHeadCreatorDto
  shared_chatters: number
  shared_regulars: number
  jaccard_chatters: number | null
  jaccard_regulars: number | null
  computed_at: string | null
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

export const retrieveCreatorHeadToHead = (creatorA: number, creatorB: number) =>
  api.get<CreatorHeadToHeadDto>(`/community/head-to-head?${buildQuery({
    creator_a: creatorA,
    creator_b: creatorB,
  })}`)
