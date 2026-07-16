import { useQuery } from '@tanstack/react-query'
import { retrieveAllCreators } from '@/lib/api/creators'
import {
    requireArray, requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'

/** @typedef {{creatorId:number, nick:string}} Creator */
/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<Creator[], Error, Creator[], readonly unknown[]>, 'queryKey'|'queryFn'>} CreatorQueryOptions */

export const creatorKeys = {
    all: ['creators'],
    list: () => [...creatorKeys.all, 'list'],
}

/** @param {unknown} value @returns {Creator} */
export const mapCreatorRow = value => {
    const row = requireRecord(value, 'creator')
    return {
        creatorId: requireFiniteNumberField(row, 'creator_id', 'creator'),
        nick: requireStringField(row, 'display_name', 'creator'),
    }
}

/** @param {Creator} creator */
export const mapCreatorOption = creator => ({
    value: creator.creatorId,
    label: creator.nick,
})

/** @param {CreatorQueryOptions & {enabled?:boolean}} [settings] */
export const useCreators = ({ enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: creatorKeys.list(),
    queryFn: async () => {
        const response = await retrieveAllCreators()
        return requireArray(response.data, 'creators').map(mapCreatorRow)
    },
    enabled,
    staleTime: 1000 * 60 * 10,
})
