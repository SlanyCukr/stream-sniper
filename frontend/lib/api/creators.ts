import { api, buildQuery } from './client'

export interface CreatorRegularsRequest {
  minStreams?: number
  sort?: string
  dir?: 'asc' | 'desc'
  limit?: number
}

export interface CreatorSummaryDto {
  creator_id: number
  nick: string
  display_name: string
  profile_image_url: string | null
  twitch_id: string | null
  total_streams: number
  first_stream_at: string | null
  last_stream_at: string | null
  total_messages: number
  duration_seconds: number | null
  messages_per_minute: number | null
  audience_size: number
  regulars: number
  latest_stream: { stream_id: number, title: string, start: string | null } | null
}

export interface CreatorTrendsDto {
  points: Array<{
    stream_id: number
    title: string
    start: string
    duration_seconds: number | null
    messages_per_minute: number | null
    unique_chatters: number
    new_chatters: number
    returning_chatters: number
    message_count: number
  }>
}

export interface CreatorRegularsDto {
  regulars: Array<{
    chatter_id: number
    nick: string
    streams_attended: number
    attendance_rate: number
    first_seen: string
    last_seen: string
    message_count: number
  }>
  total_streams: number
}

export interface AudienceAssociationDto {
  creator_id: number
  nick: string
  display_name: string
  chatter_count: number
}

export interface AudienceMovementDto {
  creator_id: number
  window_days: number
  current_audience: number
  previous_audience: number
  retained: number
  gained: number
  lapsed: number
  retention_rate: number | null
  gain_rate: number | null
  prior_channels_for_gained: AudienceAssociationDto[]
  current_channels_for_lapsed: AudienceAssociationDto[]
}

export interface CreatorEmotesDto {
  emotes: Array<{
    name: string
    source: string
    provider_id: string | null
    usage_count: number
    chatter_count: number
    stream_count: number
  }>
}
export interface CreatorRowDto {
  creator_id: number
  display_name: string
}
export type CreatorListDto = CreatorRowDto[]

export const retrieveAllCreators = () => api.get<CreatorListDto>('/creators')

export const retrieveCreatorSummary = (creatorId: number) =>
  api.get<CreatorSummaryDto>(`/creators/${creatorId}/summary`)

export const retrieveCreatorTrends = (creatorId: number) =>
  api.get<CreatorTrendsDto>(`/creators/${creatorId}/trends`)

export const retrieveCreatorRegulars = (creatorId: number, request: CreatorRegularsRequest = {}) =>
  api.get<CreatorRegularsDto>(`/creators/${creatorId}/regulars?${buildQuery({
    min_streams: request.minStreams,
    sort: request.sort,
    dir: request.dir,
    limit: request.limit,
  })}`)

export const retrieveAudienceMovement = (creatorId: number, days = 30) =>
  api.get<AudienceMovementDto>(`/creators/${creatorId}/audience-movement?${buildQuery({ days })}`)

export const retrieveCreatorEmotes = (creatorId: number, limit = 25) =>
  api.get<CreatorEmotesDto>(`/creators/${creatorId}/emotes?${buildQuery({ limit })}`)
