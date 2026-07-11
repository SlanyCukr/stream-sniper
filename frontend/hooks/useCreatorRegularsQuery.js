import { useQuery } from '@tanstack/react-query'
import { retrieveCreatorRegulars } from '@/lib/api'

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
    list: (creatorId, filters) => [
        ...creatorRegularsKeys.lists(),
        {
            creatorId,
            ...filters,
        },
    ],
}

/**
 * Custom hook for a creator's recurring chatters ("regulars"), mapped to camelCase.
 * @param {string|number} creatorId - The creator ID
 * @param {object} filters - Sort/threshold filters
 * @param {number} [filters.minStreams] - Minimum streams attended
 * @param {string} [filters.sort] - Sort column (attendance|streams|last_seen|messages)
 * @param {('asc'|'desc')} [filters.dir] - Sort direction
 * @param {number} [filters.limit] - Max rows to return
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {regulars: [{chatterId, nick, streamsAttended,
 *   attendanceRate, firstSeen, lastSeen, messageCount}], totalStreams}
 */
export const useCreatorRegulars = (creatorId, {
    minStreams,
    sort,
    dir,
    limit,
} = {}, options = {}) => useQuery({
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
        const data = response.data || {
        }
        return {
            regulars: (data.regulars || []).map(r => ({
                chatterId: r.chatter_id,
                nick: r.nick,
                streamsAttended: r.streams_attended,
                attendanceRate: r.attendance_rate,
                firstSeen: r.first_seen,
                lastSeen: r.last_seen,
                messageCount: r.message_count,
            })),
            totalStreams: data.total_streams,
        }
    },
    enabled: Boolean(creatorId), // Only enabled when creatorId is provided
    ...options,
})
