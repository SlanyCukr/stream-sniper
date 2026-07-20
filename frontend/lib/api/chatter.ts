import { getJson } from './client'
import type { ArchetypeBadgeDto, HomeChannelDto } from './sharedDtos'

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
) => getJson<ChatterMessagePageDto>(
  `/chatters/${chatterId}/messages`,
  { offset: rowOffset, limit: pageSize },
)

export const retrieveChatterSearch = (query: string, limit = 10) =>
  getJson<ChatterSearchDto>('/chatters/search', { q: query, limit })

export const retrieveChatterStreamActivity = (chatterId: number) =>
  getJson<ChatterStreamActivityDto>(`/chatters/${chatterId}/stream-activity`)

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
  home_channel: HomeChannelDto | null
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
  // (empty array when no badge applies).
  archetypes: ArchetypeBadgeDto[]
}

export const retrieveChatterPassport = (chatterId: number) =>
  getJson<ChatterPassportDto>(`/chatters/${chatterId}/passport`)

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
  home_channel: HomeChannelDto | null
  archetypes: ArchetypeBadgeDto[]
}

export interface ChatterHeadToHeadDto {
  a: ChatterHeadToHeadSideDto
  b: ChatterHeadToHeadSideDto
  shared_streams: number
  shared_creators: number
}

export const retrieveChatterHeadToHead = (chatterA: number, chatterB: number) =>
  getJson<ChatterHeadToHeadDto>('/chatters/head-to-head', { chatter_a: chatterA, chatter_b: chatterB })
