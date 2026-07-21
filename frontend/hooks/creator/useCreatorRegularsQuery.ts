import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveCreatorRegulars } from '@/lib/api/creators'
import {
    requireArrayField, requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'
import { creatorKeys } from './creatorKeys'

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
    queryKey: creatorKeys.regulars(creatorId, {
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
            regulars: requireArrayField(data, 'regulars', 'creator regulars').map((raw, index) => {
                const label = `creator regulars.regulars[${index}]`
                const regular = requireRecord(raw, label)
                return {
                    chatterId: requireFiniteNumberField(regular, 'chatter_id', label),
                    nick: requireStringField(regular, 'nick', label),
                    streamsAttended: requireFiniteNumberField(regular, 'streams_attended', label),
                    attendanceRate: requireFiniteNumberField(regular, 'attendance_rate', label),
                    firstSeen: requireStringField(regular, 'first_seen', label),
                    lastSeen: requireStringField(regular, 'last_seen', label),
                    messageCount: requireFiniteNumberField(regular, 'message_count', label),
                }
            }),
            totalStreams: requireFiniteNumberField(data, 'total_streams', 'creator regulars'),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
