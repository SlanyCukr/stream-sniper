/** Shared view-model shapes for the scene search surface (produced by the
 * mappers in hooks/scene/useSearchQueries.js and consumed by the .tsx views). */

export interface SearchHitVM {
  messageId: number
  time: string
  text: string
  chatter: { id: number, nick: string, isBot: boolean | null }
  stream: { id: number, title: string }
  creator: { id: number, nick: string, displayName: string }
}

export interface SearchFirstVM {
  query: string
  totalMatches: number
  first: SearchHitVM | null
  byCreator: SearchHitVM[]
}

export interface SearchFrequencyPoint {
  date: string
  count: number
}

export interface SearchContextMessageVM {
  id: number
  time: string
  chatterId: number
  nick: string
  text: string
  isSubscriber: boolean
  badges: string[]
}

export interface SearchContextVM {
  stream: { id: number, title: string, creator: { id: number, nick: string, displayName: string } }
  messages: SearchContextMessageVM[]
  hitIndex: number
}
