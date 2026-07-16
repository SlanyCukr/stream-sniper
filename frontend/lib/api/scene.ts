import { api, buildQuery } from './client'

export interface SceneCopypastaRequest {
  days?: number
  creatorId?: number
  sort?: 'usage' | 'spread' | 'recent'
  pageSize?: number
  rowOffset?: number
}

export interface ScenePulseRequest {
  days?: number
  eventType?: string
  creatorId?: number
  limit?: number
  offset?: number
}

export interface SceneLiveDto {
  live: Array<{
    creator_id: number
    nick: string
    display_name: string | null
    profile_image_url: string | null
    viewer_count: number | null
    title: string | null
    session_started_at: string | null
    sampled_at: string | null
  }>
  live_count: number
  last_sample_at: string | null
}

export interface SceneLeaderboardDto {
  window_days: 7 | 30
  computed_at: string | null
  entries: Array<{
    rank: number
    creator_id: number
    nick: string
    display_name: string | null
    profile_image_url: string | null
    streams: number
    hours_streamed: number | null
    total_messages: number
    msgs_per_min: number | null
    chatter_appearances: number
    peak_viewers: number | null
  }>
}

export interface SceneCopypastasDto {
  total: number
  offset: number
  limit: number
  items: Array<{
    message_text_id: number
    text: string
    usage_count: number
    chatter_appearances: number
    stream_count: number
    creator_count: number
    first_seen: string | null
    last_stream_start: string | null
  }>
}

export interface CopypastaPropagationDto {
  message_text_id: number
  text: string
  usage_count: number
  chatter_appearances: number
  stream_count: number
  creator_count: number
  first_seen: string | null
  occurrences: Array<{
    stream_id: number
    creator_id: number
    nick: string
    display_name: string
    profile_image_url: string | null
    stream_title: string
    stream_start: string | null
    first_seen: string | null
    usage_count: number
    chatter_count: number
  }>
  origin_context: Array<{
    id: number
    time: string
    chatter_id: number
    nick: string
    text: string
  }>
}

export interface ScenePulseDto {
  total: number
  days: number
  limit: number
  offset: number
  items: Array<{
    id: number
    event_type: string
    occurred_at: string
    creator_id: number | null
    creator_nick: string | null
    creator_display_name: string | null
    stream_id: number | null
    message_text_id: number | null
    title: string
    summary: string
    metadata: Record<string, unknown>
  }>
}

export interface SceneDigestDto {
  days: number
  markdown: string
}

export const retrieveSceneLive = () => api.get<SceneLiveDto>('/scene/live')

export const retrieveSceneLeaderboard = (windowDays: 7 | 30 = 7) =>
  api.get<SceneLeaderboardDto>(`/scene/leaderboard?${buildQuery({ window: windowDays })}`)

export const retrieveSceneCopypastas = (request: SceneCopypastaRequest = {}) =>
  api.get<SceneCopypastasDto>(`/scene/copypastas?${buildQuery({
    days: request.days,
    creator_id: request.creatorId,
    sort: request.sort,
    limit: request.pageSize,
    offset: request.rowOffset,
  })}`)

export const retrieveCopypastaPropagation = (messageTextId: number, contextSeconds = 90) =>
  api.get<CopypastaPropagationDto>(
    `/scene/copypastas/${messageTextId}?${buildQuery({ context_seconds: contextSeconds })}`,
  )

export const retrieveScenePulse = (request: ScenePulseRequest = {}) =>
  api.get<ScenePulseDto>(`/scene/pulse?${buildQuery({
    days: request.days,
    event_type: request.eventType,
    creator_id: request.creatorId,
    limit: request.limit,
    offset: request.offset,
  })}`)

export const retrieveSceneDigest = (days = 7) =>
  api.get<SceneDigestDto>(`/scene/digest?${buildQuery({ days })}`)
