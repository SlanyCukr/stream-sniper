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

// ---------------------------------------------------------------------------
// Scene power rankings (chatter leaderboard) — GET /scene/chatter-rankings
// ---------------------------------------------------------------------------

export type RankingsWindow = 'all' | '7' | '30'

export interface SceneRankingsRequest {
  window?: RankingsWindow
  limit?: number
  offset?: number
}

export interface SceneRankingsDto {
  window: string
  has_more: boolean
  items: Array<{
    rank: number
    chatter_id: number
    nick: string
    total_messages: number
    streams_attended: number
    creators_visited: number
    home_channel: {
      creator_id: number
      creator_nick: string
      creator_display_name: string
      messages: number
      share: number
    } | null
  }>
}

export const retrieveSceneRankings = (request: SceneRankingsRequest = {}) =>
  api.get<SceneRankingsDto>(`/scene/chatter-rankings?${buildQuery({
    window: request.window,
    limit: request.limit,
    offset: request.offset,
  })}`)

// ---------------------------------------------------------------------------
// Scene highlights wall (hype-ranked moments) — GET /scene/highlights
// ---------------------------------------------------------------------------

export type HighlightsWindow = 'all' | '7' | '30'
export type HighlightsSort = 'hype' | 'recent'

export interface SceneHighlightsRequest {
  window?: HighlightsWindow
  creatorId?: number
  sort?: HighlightsSort
  limit?: number
  offset?: number
}

export interface SceneHighlightsDto {
  window: string
  sort: string
  has_more: boolean
  items: Array<{
    stream_id: number
    stream_title: string
    twitch_id: string | null
    creator_id: number
    creator_nick: string
    creator_display_name: string
    bucket_minute: string
    offset_seconds: number
    ratio: number | null
    message_count: number
    unique_chatters: number
    sub_share: number | null
    emote_share: number | null
    top_phrases: Array<{ phrase: string, count: number, lift: number }> | null
    sample_messages: Array<{ text: string, count: number }> | null
    clip_url: string | null
    review_status: string | null
  }>
}

export const retrieveSceneHighlights = (request: SceneHighlightsRequest = {}) =>
  api.get<SceneHighlightsDto>(`/scene/highlights?${buildQuery({
    window: request.window,
    creator_id: request.creatorId,
    sort: request.sort,
    limit: request.limit,
    offset: request.offset,
  })}`)

// ---------------------------------------------------------------------------
// Scene trending velocity — GET /scene/trending/{copypastas,emotes}
// ---------------------------------------------------------------------------

export type TrendingWindow = 7 | 14 | 30

export interface SceneTrendingRequest {
  window?: TrendingWindow
  creatorId?: number
  limit?: number
}

export interface TrendingCopypastasDto {
  window: number
  items: Array<{
    message_text_id: number
    text: string
    current_usage: number
    prior_usage: number
    delta_pct: number | null
    trend: string
    stream_count: number
    creator_count: number
    first_seen: string | null
  }>
}

export interface TrendingEmotesDto {
  window: number
  items: Array<{
    emote_id: number
    name: string
    source: string
    provider_id: string | null
    current_usage: number
    prior_usage: number
    delta_pct: number | null
    trend: string
    chatter_reach: number
    creator_count: number
    first_seen: string | null
  }>
}

export const retrieveTrendingCopypastas = (request: SceneTrendingRequest = {}) =>
  api.get<TrendingCopypastasDto>(`/scene/trending/copypastas?${buildQuery({
    window: request.window,
    creator_id: request.creatorId,
    limit: request.limit,
  })}`)

export const retrieveTrendingEmotes = (request: SceneTrendingRequest = {}) =>
  api.get<TrendingEmotesDto>(`/scene/trending/emotes?${buildQuery({
    window: request.window,
    creator_id: request.creatorId,
    limit: request.limit,
  })}`)

// ---------------------------------------------------------------------------
// Scene Wrapped (period recap) — GET /scene/wrapped
// ---------------------------------------------------------------------------

export interface SceneWrappedDto {
  days: number
  totals: {
    streams: number
    hours_streamed: number | null
    messages: number
    active_chatters: number
    creators_active: number
  }
  top_creators: Array<{
    rank: number
    creator_id: number
    nick: string
    display_name: string
    profile_image_url: string | null
    total_messages: number
    streams: number
    hours_streamed: number | null
    msgs_per_min: number | null
    peak_viewers: number | null
  }>
  top_chatters: Array<{
    rank: number
    chatter_id: number
    nick: string
    total_messages: number
    streams_attended: number
    creators_visited: number
    home_creator_display_name: string | null
  }>
  top_moments: Array<{
    stream_id: number
    stream_title: string
    twitch_id: string | null
    creator_display_name: string
    bucket_minute: string
    offset_seconds: number
    ratio: number | null
    message_count: number
  }>
  top_copypastas: Array<{
    message_text_id: number
    text: string
    usage_count: number
    creator_count: number
    stream_count: number
  }>
  top_emotes: Array<{
    emote_id: number
    name: string
    source: string
    usage: number
    chatter_reach: number
  }>
  notable_events: Array<{
    event_type: string
    occurred_at: string
    title: string
    summary: string
    creator_display_name: string | null
  }>
}

export const retrieveSceneWrapped = (days = 30) =>
  api.get<SceneWrappedDto>(`/scene/wrapped?${buildQuery({ days })}`)

// ---------------------------------------------------------------------------
// Live Moment Radar (chat velocity for live streams) — GET /scene/radar
// ---------------------------------------------------------------------------

export interface SceneRadarDto {
  generated_at: string
  channels: Array<{
    stream_id: number
    creator_id: number
    creator_nick: string
    creator_display_name: string
    profile_image_url: string | null
    stream_title: string | null
    started_at: string | null
    messages_last_minute: number
    unique_chatters_last_minute: number
    baseline_per_minute: number | null
    ratio: number | null
    spiking: boolean
    minutes: Array<{ minute: string, messages: number }>
  }>
}

export const retrieveSceneRadar = () =>
  api.get<SceneRadarDto>('/scene/radar')

// ---------------------------------------------------------------------------
// Emote drill-down (lifetime story of one emote) — GET /scene/emotes/{id}
// ---------------------------------------------------------------------------

export interface EmoteDetailDto {
  meta: {
    emote_id: number
    name: string
    source: string
    provider_id: string | null
    first_seen: string | null
  }
  totals: {
    usage: number
    chatter_reach: number
    stream_count: number
    creator_count: number
    last_used: string | null
  }
  top_creators: Array<{
    creator_id: number
    nick: string
    display_name: string
    usage: number
    chatter_reach: number
    stream_count: number
  }>
  weekly_usage: Array<{ week_start: string, usage: number }>
  recent_streams: Array<{
    stream_id: number
    title: string | null
    start: string | null
    creator_id: number
    creator_nick: string
    creator_display_name: string
    usage: number
    chatter_count: number
  }>
}

export const retrieveEmoteDetail = (emoteId: number) =>
  api.get<EmoteDetailDto>(`/scene/emotes/${emoteId}`)
