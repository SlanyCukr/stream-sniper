import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveAllCreators } from '@/lib/api/creators'
import {
    requireArray, requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'

export interface Creator {
    creatorId: number
    nick: string
}

export interface CreatorOption {
    value: number
    label: string
}

type CreatorQueryOptions = Omit<
    UseQueryOptions<Creator[], Error, Creator[], readonly unknown[]>,
    'queryKey' | 'queryFn'
>

const creatorKeys = {
    all: ['creators'],
    list: () => [...creatorKeys.all, 'list'],
}

export const mapCreatorRow = (value: unknown): Creator => {
    const row = requireRecord(value, 'creator')
    return {
        creatorId: requireFiniteNumberField(row, 'creator_id', 'creator'),
        nick: requireStringField(row, 'display_name', 'creator'),
    }
}

export const mapCreatorOption = (creator: Creator): CreatorOption => ({
    value: creator.creatorId,
    label: creator.nick,
})

export const useCreators = (
    { enabled = true, ...options }: CreatorQueryOptions & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: creatorKeys.list(),
    queryFn: async () => {
        const response = await retrieveAllCreators()
        return requireArray(response.data, 'creators').map(mapCreatorRow)
    },
    enabled,
    staleTime: 1000 * 60 * 10,
})
