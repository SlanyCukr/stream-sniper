import { getJson } from './client'

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

export interface CreatorWrappedDto {
  creator_id: number
  days: number
  totals: {
    streams: number
    hours_streamed: number | null
    messages: number
    active_chatters: number
  }
  top_chatters: Array<{
    rank: number
    chatter_id: number
    nick: string
    total_messages: number
    streams_attended: number
  }>
  top_moments: Array<{
    stream_id: number
    stream_title: string
    twitch_id: string | null
    bucket_minute: string
    offset_seconds: number
    ratio: number | null
    message_count: number
  }>
  top_copypastas: Array<{
    message_text_id: number
    text: string
    usage_count: number
    stream_count: number
  }>
  top_emotes: Array<{
    emote_id: number
    name: string
    source: string
    usage: number
    chatter_reach: number
  }>
}
export interface CreatorRowDto {
  creator_id: number
  display_name: string
}
export type CreatorListDto = CreatorRowDto[]

export const retrieveAllCreators = () => getJson<CreatorListDto>('/creators')

export const retrieveCreatorSummary = (creatorId: number) =>
  getJson<CreatorSummaryDto>(`/creators/${creatorId}/summary`)

export const retrieveCreatorTrends = (creatorId: number) =>
  getJson<CreatorTrendsDto>(`/creators/${creatorId}/trends`)

export const retrieveCreatorRegulars = (creatorId: number, request: CreatorRegularsRequest = {}) =>
  getJson<CreatorRegularsDto>(`/creators/${creatorId}/regulars`, {
    min_streams: request.minStreams,
    sort: request.sort,
    dir: request.dir,
    limit: request.limit,
  })

export const retrieveAudienceMovement = (creatorId: number, days = 30) =>
  getJson<AudienceMovementDto>(`/creators/${creatorId}/audience-movement`, { days })

export const retrieveCreatorEmotes = (creatorId: number, limit = 25) =>
  getJson<CreatorEmotesDto>(`/creators/${creatorId}/emotes`, { limit })

export const retrieveCreatorWrapped = (creatorId: number, days = 30) =>
  getJson<CreatorWrappedDto>(`/creators/${creatorId}/wrapped`, { days })
