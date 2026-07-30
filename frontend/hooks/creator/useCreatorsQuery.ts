import { retrieveAllCreators } from '@/lib/api/creators'
import {
    requireArray, requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'
import { defineQuery, type QueryOptions } from '@/hooks/defineQuery'
import { creatorKeys } from './creatorKeys'

export interface Creator {
    creatorId: number
    nick: string
}

export interface CreatorOption {
    value: number
    label: string
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

const creatorsQuery = defineQuery({
    key: () => creatorKeys.catalog(),
    fetch: () => retrieveAllCreators(),
    map: (value: unknown) => requireArray(value, 'creators').map(mapCreatorRow),
})

export const useCreators = (
    options: QueryOptions<Creator[]> = {},
) => creatorsQuery(undefined, { ...options, staleTime: 1000 * 60 * 10 })
