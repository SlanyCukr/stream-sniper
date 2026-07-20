import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveCreatorRegulars, type CreatorRegularsDto } from '@/lib/api/creators'
import {
    requireArrayField, requireFiniteNumberField, requireRecord,
} from '@/lib/api/contractGuards'

export interface CreatorRegular {
    chatterId: number
    nick: string
    streamsAttended: number
    attendanceRate: number
    firstSeen: string
    lastSeen: string
    messageCount: number
}

export interface CreatorRegulars {
    regulars: CreatorRegular[]
    totalStreams: number
}

interface CreatorRegularsFilters {
    minStreams?: number
    sort?: string
    dir?: 'asc' | 'desc'
    limit?: number
}

type QueryOptions = Omit<
    UseQueryOptions<CreatorRegulars, Error, CreatorRegulars, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

/**
 * Query key factory for creator "regulars" queries
 */
export const creatorRegularsKeys = {
    all: [
        'creator-regulars',
    ],
    lists: () => [
        ...creatorRegularsKeys.all,
        'list',
    ],
    list: (creatorId: number, filters: CreatorRegularsFilters) => [
        ...creatorRegularsKeys.lists(),
        {
            creatorId,
            ...filters,
        },
    ],
}

/**
 * Custom hook for a creator's recurring chatters ("regulars"), mapped to camelCase.
 * @param creatorId - The normalized creator ID
 * @param filters - Sort/threshold filters
 * @param options - Additional query options
 * @returns useQuery result; data = {regulars: [{chatterId, nick, streamsAttended,
 *   attendanceRate, firstSeen, lastSeen, messageCount}], totalStreams}
 */
export const useCreatorRegulars = (creatorId: number, {
    minStreams,
    sort,
    dir,
    limit,
}: CreatorRegularsFilters = {}, { enabled = true, ...options }: QueryOptions & { enabled?: boolean } = {}) => useQuery({
    ...options,
    queryKey: creatorRegularsKeys.list(creatorId, {
        minStreams,
        sort,
        dir,
        limit,
    }),
    queryFn: async () => {
        const response = await retrieveCreatorRegulars(creatorId, {
            minStreams,
            sort,
            dir,
            limit,
        })
        const data = requireRecord(response, 'creator regulars')
        return {
            regulars: requireArrayField(data, 'regulars', 'creator regulars').map(raw => {
                // requireArrayField only checks the collection shape; individual rows
                // are trusted against the wire DTO rather than guarded field-by-field
                // (matches existing behavior).
                const r = raw as CreatorRegularsDto['regulars'][number]
                return {
                    chatterId: r.chatter_id,
                    nick: r.nick,
                    streamsAttended: r.streams_attended,
                    attendanceRate: r.attendance_rate,
                    firstSeen: r.first_seen,
                    lastSeen: r.last_seen,
                    messageCount: r.message_count,
                }
            }),
            totalStreams: requireFiniteNumberField(data, 'total_streams', 'creator regulars'),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
