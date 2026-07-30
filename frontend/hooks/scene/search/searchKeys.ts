import { sceneKeys } from '../sceneKeys'

interface SearchMessagesFilters {
    q: string
    creatorId: number | null
    days: number | null
    limit: number
}

interface SearchFirstFilters {
    q: string
    creatorId: number | null
}

interface SearchFrequencyFilters {
    q: string
    days: number | null
    creatorId: number | null
}

interface SearchContextParams {
    streamId: number | null
    messageId: number | null
    radius: number | null
}

export const searchKeys = {
    all: () => [...sceneKeys.all, 'search'] as const,
    messages: (filters: SearchMessagesFilters) => [...searchKeys.all(), 'messages', filters] as const,
    first: (filters: SearchFirstFilters) => [...searchKeys.all(), 'first', filters] as const,
    frequency: (filters: SearchFrequencyFilters) => [...searchKeys.all(), 'frequency', filters] as const,
    context: (params: SearchContextParams) => [...searchKeys.all(), 'context', params] as const,
}
