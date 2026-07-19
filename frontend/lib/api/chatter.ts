import { api, buildQuery } from './client'

export interface ChatterMessagePageDto {
  messages: Array<{
    stream_id: number
    stream_title: string
    creator_display_name: string
    text: string
    timestamp: string
  }>
  total: number
  offset: number
  limit: number
}

export type ChatterSearchDto = Array<{ chatter_id: number, nick: string, is_bot: boolean | null }>
export type ChatterStreamActivityDto = Array<{
  stream_id: number
  stream_title: string
  start: string
  creator_id: number
  creator_display_name: string
  message_count: number
  is_bot: boolean | null
}>

export const retrieveChatterMessages = (
  chatterId: number,
  { rowOffset = 0, pageSize = 50 }: { rowOffset?: number, pageSize?: number } = {},
) => api.get<ChatterMessagePageDto>(
  `/chatters/${chatterId}/messages?${buildQuery({ offset: rowOffset, limit: pageSize })}`,
)

export const retrieveChatterSearch = (query: string, limit = 10) =>
  api.get<ChatterSearchDto>(`/chatters/search?${buildQuery({ q: query, limit })}`)

export const retrieveChatterStreamActivity = (chatterId: number) =>
  api.get<ChatterStreamActivityDto>(`/chatters/${chatterId}/stream-activity`)

export interface ChatterPassportDto {
  chatter: {
    id: number
    nick: string
    is_bot: boolean | null
    bot_reason: string | null
  }
  totals: {
    messages: number
    streams_attended: number
    creators_visited: number
    first_seen: string | null
    last_seen: string | null
  }
  debut: {
    stream_id: number
    stream_title: string
    creator_display_name: string
    time: string
  } | null
  home_channel: {
    creator_id: number
    creator_nick: string
    creator_display_name: string
    messages: number
    share: number
  } | null
  loyalty: Array<{
    creator_id: number
    creator_nick: string
    creator_display_name: string
    messages: number
    streams_attended: number
    share: number
  }>
  milestones: {
    most_active_stream: {
      stream_id: number
      title: string
      creator_display_name: string
      messages: number
    } | null
  }
  // Rule-based identity badges derived from the passport's own data. Always present
  // (empty array when no badge applies); each entry is a stable key + label + reason.
  archetypes: Array<{
    key: string
    label: string
    description: string
  }>
}

export const retrieveChatterPassport = (chatterId: number) =>
  api.get<ChatterPassportDto>(`/chatters/${chatterId}/passport`)

// ---------------------------------------------------------------------------
// Chatter head-to-head — GET /chatters/head-to-head
// ---------------------------------------------------------------------------

interface ChatterHeadToHeadSideDto {
  chatter_id: number
  nick: string
  is_bot: boolean | null
  messages: number
  streams_attended: number
  creators_visited: number
  first_seen: string | null
  last_seen: string | null
  home_channel: {
    creator_id: number
    creator_nick: string
    creator_display_name: string
    messages: number
    share: number
  } | null
  archetypes: Array<{ key: string, label: string, description: string }>
}

export interface ChatterHeadToHeadDto {
  a: ChatterHeadToHeadSideDto
  b: ChatterHeadToHeadSideDto
  shared_streams: number
  shared_creators: number
}

export const retrieveChatterHeadToHead = (chatterA: number, chatterB: number) =>
  api.get<ChatterHeadToHeadDto>(`/chatters/head-to-head?${buildQuery({ chatter_a: chatterA, chatter_b: chatterB })}`)
