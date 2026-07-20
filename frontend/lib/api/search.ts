import { getJson } from './client'

export interface SearchMessagesRequest {
  q: string
  creatorId?: number
  days?: number
  limit?: number
  offset?: number
}

export interface SearchFirstRequest {
  q: string
  creatorId?: number
}

export interface SearchFrequencyRequest {
  q: string
  days?: number
  creatorId?: number
}

export interface SearchContextRequest {
  streamId: number
  messageId: number
  radius?: number
}

export interface SearchHitDto {
  message_id: number
  time: string
  text: string
  chatter: { id: number, nick: string, is_bot: boolean | null }
  stream: { id: number, title: string }
  creator: { id: number, nick: string, display_name: string }
}

export interface SearchMessagesDto {
  query: string
  items: SearchHitDto[]
  has_more: boolean
}

export interface SearchFirstDto {
  query: string
  first: SearchHitDto | null
  by_creator: SearchHitDto[]
  total_matches: number
}

export interface SearchFrequencyDto {
  query: string
  days: number
  points: Array<{ date: string, count: number }>
}

export interface SearchContextMessageDto {
  id: number
  time: string
  chatter_id: number
  nick: string
  text: string
  is_subscriber: boolean
  badges: string[]
}

export interface SearchContextDto {
  stream: { id: number, title: string, creator: { id: number, nick: string, display_name: string } }
  messages: SearchContextMessageDto[]
  hit_index: number
}

export const retrieveSearchMessages = (request: SearchMessagesRequest) =>
  getJson<SearchMessagesDto>('/search/messages', {
    q: request.q,
    creator_id: request.creatorId,
    days: request.days,
    limit: request.limit,
    offset: request.offset,
  })

export const retrieveSearchFirst = (request: SearchFirstRequest) =>
  getJson<SearchFirstDto>('/search/first', {
    q: request.q,
    creator_id: request.creatorId,
  })

export const retrieveSearchFrequency = (request: SearchFrequencyRequest) =>
  getJson<SearchFrequencyDto>('/search/frequency', {
    q: request.q,
    days: request.days,
    creator_id: request.creatorId,
  })

export const retrieveSearchContext = (request: SearchContextRequest) =>
  getJson<SearchContextDto>('/search/context', {
    stream_id: request.streamId,
    message_id: request.messageId,
    radius: request.radius,
  })
