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

export interface ChatterIdentityDto {
  chatter_id: number
  is_bot: boolean | null
}
export type ChatterSearchDto = Array<{ chatter_id: number, nick: string, is_bot: boolean | null }>
export type ChatterListDto = Array<{ chatter_id: number, nick: string }>
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

export const retrieveChatterIdentity = (nick: string) =>
  api.get<ChatterIdentityDto>(`/chatters/by-nick/${nick}`)

export const retrieveChatterSearch = (query: string, limit = 10) =>
  api.get<ChatterSearchDto>(`/chatters/search?${buildQuery({ q: query, limit })}`)

export const retrieveChattersOnStream = (streamId: number) =>
  api.get<ChatterListDto>(`/streams/${streamId}/chatters`)

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
}

export const retrieveChatterPassport = (chatterId: number) =>
  api.get<ChatterPassportDto>(`/chatters/${chatterId}/passport`)
