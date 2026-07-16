import { api, buildQuery } from './client'

export interface StreamListRequest {
  creatorId: number
  sort?: string
  dir?: 'asc' | 'desc'
  title?: string
  dateFrom?: string
  dateTo?: string
  minMessages?: number
  rowOffset?: number
  pageSize?: number
}

export interface StreamListRowDto {
  stream_id: number
  creator_name: string
  start: string
  end: string | null
  thumbnail_url: string | null
  message_count: number
}

export interface StreamListDto {
  streams: StreamListRowDto[]
  total: number
  offset: number
  limit: number
}

export interface StreamMessageRequest {
  chatterId?: number
  q?: string
  afterTs?: string
  afterId?: number
  limit?: number
  subOnly?: boolean
}

export interface StreamMessageDto {
  id: number
  time: string
  chatter_id: number
  nick: string
  text: string
  is_subscriber: boolean
  badges: string[]
}

export interface StreamMessagesDto {
  messages: StreamMessageDto[]
  next_cursor: { after_ts: string, after_id: number } | null
  has_more: boolean
}

export interface TimelineBucketDto {
  bucket_minute: string
  message_count: number
  unique_chatters: number
  sub_messages: number | null
  emote_messages: number | null
}

export interface TimelineMomentDto {
  bucket_minute: string
  offset_seconds: number | null
  message_count: number
  ratio: number | null
  persisted: boolean
  status: string | null
  sub_share: number | null
  emote_share: number | null
  top_phrases: Array<Record<string, unknown>> | null
  sample_messages: Array<Record<string, unknown>> | null
}

export interface TimelineMetricsDto {
  unique_chatters: number
  messages_per_minute: number | null
  peak_bucket_minute: string | null
  new_chatters: number
  returning_chatters: number
  total_messages: number
  duration_seconds: number | null
  peak_messages: number
  sub_messages: number | null
  emote_messages: number | null
}

export interface StreamTimelineDto {
  stream_id: number
  stream_start: string | null
  twitch_id: string | null
  bucket_seconds: number
  buckets: TimelineBucketDto[]
  moments: TimelineMomentDto[]
  metrics: TimelineMetricsDto | null
  viewer_samples: Array<{ t: string, viewer_count: number }>
  peak_viewers: number | null
  context_changes: Array<{
    t: string
    title: string | null
    category_id: string | null
    category_name: string | null
    language: string | null
    tags: string[]
    is_mature: boolean | null
  }>
}

export interface StreamComparisonDto {
  streams: Array<{
    stream_id: number
    creator_id: number
    creator_nick: string
    creator_display_name: string
    title: string
    start: string | null
    duration_seconds: number | null
    total_messages: number | null
    messages_per_minute: number | null
    unique_chatters: number | null
    new_chatters: number | null
    returning_chatters: number | null
    sub_share: number | null
    emote_share: number | null
    peak_messages: number | null
    peak_bucket_minute: string | null
    peak_viewers: number | null
    curve: Array<{ percent: number, message_count: number, unique_chatters: number }>
  }>
  retention: Array<{
    from_stream_id: number
    to_stream_id: number
    from_audience: number
    to_audience: number
    retained: number
    retention_rate: number | null
  }>
}

export interface ReportMetricDto {
  value: number | null
  delta_pct: number | null
  percentile: number | null
  baseline_median: number | null
}

export interface StreamReportDto {
  stream_id: number
  creator_id: number
  creator_nick: string | null
  title: string | null
  start: string | null
  end: string | null
  duration_seconds: number | null
  baseline_count: number
  lookback: number
  metrics: Record<
    'messages_per_minute' | 'total_messages' | 'unique_chatters' | 'new_chatters'
    | 'returning_chatters' | 'sub_share' | 'peak_messages' | 'avg_viewers' | 'peak_viewers',
    ReportMetricDto
  >
  peak_bucket_minute: string | null
  top_emote: {
    name: string
    source: string
    provider_id: string | null
    usage_count: number
    chatter_count: number
  } | null
  top_phrase: { phrase: string, usage_count: number, chatter_count: number } | null
  top_moments: Array<{
    bucket_minute: string
    offset_seconds: number | null
    message_count: number
    ratio: number | null
    status: string | null
  }>
}

export interface StreamDto {
  info: {
    title: string | null
    start: string
    end: string | null
    thumbnail_url: string | null
    message_count: number
    creator_nick: string
    creator_display_name: string
    profile_image_url: string | null
    creator_id: number
  }
  most_active_chatters: Array<{ chatter_id: number, nick: string, count: number }>
  most_tagged_chatters: Array<{ chatter_id: number, nick: string, count: number }>
  other_creators: Array<{ creator_id: number, nick: string }>
  chatters: Array<{ chatter_id: number, nick: string }>
}

export interface StreamMentionsDto {
  mentioned: Array<{ chatter_id: number, nick: string, count: number }>
  pairs: Array<{
    from_chatter_id: number
    from_nick: string
    to_chatter_id: number
    to_nick: string
    count: number
  }>
}

export interface StreamEmotesDto {
  emotes: Array<{
    name: string
    source: string
    provider_id: string | null
    usage_count: number
    chatter_count: number
    stream_count?: number
  }>
}

export interface StreamPhrasesDto {
  phrases: Array<{ phrase: string, usage_count: number, chatter_count: number }>
}

export const retrieveStreams = (request: StreamListRequest) => api.get<StreamListDto>(
  `/streams?${buildQuery({
    creator_id: request.creatorId,
    sort: request.sort,
    dir: request.dir,
    title: request.title,
    date_from: request.dateFrom,
    date_to: request.dateTo,
    min_messages: request.minMessages,
    offset: request.rowOffset,
    limit: request.pageSize,
  })}`,
)

export const retrieveStreamMessages = (streamId: number, request: StreamMessageRequest = {}) =>
  api.get<StreamMessagesDto>(`/streams/${streamId}/messages?${buildQuery({
    chatter_id: request.chatterId,
    q: request.q,
    after_ts: request.afterTs,
    after_id: request.afterId,
    limit: request.limit,
    sub_only: request.subOnly || null,
  })}`)

export const retrieveStreamTimeline = (streamId: number) =>
  api.get<StreamTimelineDto>(`/streams/${streamId}/timeline`)

export const retrieveStreamComparison = (streamIds: number[]) => {
  const params = new URLSearchParams()
  streamIds.forEach((id) => params.append('stream_ids', String(id)))
  return api.get<StreamComparisonDto>(`/streams/compare?${params}`)
}

export const retrieveStreamMentions = (streamId: number, limit = 20) =>
  api.get<StreamMentionsDto>(`/streams/${streamId}/mentions?${buildQuery({ limit })}`)

export const retrieveStreamEmotes = (streamId: number, limit = 25) =>
  api.get<StreamEmotesDto>(`/streams/${streamId}/emotes?${buildQuery({ limit })}`)

export const retrieveStreamPhrases = (streamId: number, limit = 25) =>
  api.get<StreamPhrasesDto>(`/streams/${streamId}/phrases?${buildQuery({ limit })}`)

export const retrieveStreamReport = (streamId: number, lookback?: number) =>
  api.get<StreamReportDto>(`/streams/${streamId}/report?${buildQuery({ lookback })}`)

export const downloadStreamExport = (streamId: number, format: 'ndjson' | 'csv' = 'ndjson') =>
  api.get<Blob>(`/streams/${streamId}/export?${buildQuery({ format })}`, {
    responseType: 'blob',
    timeout: 0,
  })

export const downloadStreamInsightCsv = (
  streamId: number,
  kind: 'emotes' | 'phrases' | 'mentions',
) => api.get<Blob>(`/streams/${streamId}/${kind}/export`, {
  responseType: 'blob',
  timeout: 0,
})

export const retrieveStreamComprehensive = (streamId: number) =>
  api.get<StreamDto>(`/streams/${streamId}`)
