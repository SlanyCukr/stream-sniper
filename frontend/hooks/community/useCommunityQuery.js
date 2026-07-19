import { useQuery } from '@tanstack/react-query'
import {
    retrieveCommunityOverlap,
    retrieveCreatorNeighbors,
} from '@/lib/api/community'
import { requireArrayField, requireRecord } from '@/lib/api/contractGuards'

const communityKeys = {
    all: ['community'],
    overlap: limit => [...communityKeys.all, 'overlap', { limit }],
    neighbors: (creatorId, metric, limit) => [...communityKeys.all, 'neighbors', { creatorId, metric, limit }],
}

export const useCommunityOverlap = ({ limit = 40 } = {}, options = {}) => useQuery({
    ...options,
    queryKey: communityKeys.overlap(limit),
    queryFn: async () => {
        const response = await retrieveCommunityOverlap(limit)
        const data = requireRecord(response.data, 'community overlap')
        return {
            creators: requireArrayField(data, 'creators', 'community overlap').map(c => ({
                creatorId: c.creator_id,
                nick: c.nick,
                displayName: c.display_name,
                chatters: c.chatters,
                regulars: c.regulars,
            })),
            pairs: requireArrayField(data, 'pairs', 'community overlap').map(p => ({
                a: p.a,
                b: p.b,
                sharedChatters: p.shared_chatters,
                sharedRegulars: p.shared_regulars,
                jaccardChatters: p.jaccard_chatters,
                jaccardRegulars: p.jaccard_regulars,
            })),
            computedAt: data.computed_at,
        }
    },
})

export const useCreatorNeighbors = (
    creatorId,
    { metric, limit } = {},
    { enabled = true, ...options } = {},
) => useQuery({
    ...options,
    queryKey: communityKeys.neighbors(creatorId, metric, limit),
    queryFn: async () => {
        const response = await retrieveCreatorNeighbors(creatorId, { metric, limit })
        const data = requireRecord(response.data, 'creator neighbors')
        return {
            neighbors: requireArrayField(data, 'neighbors', 'creator neighbors').map(n => ({
                creatorId: n.creator_id,
                nick: n.nick,
                displayName: n.display_name,
                sharedChatters: n.shared_chatters,
                sharedRegulars: n.shared_regulars,
            })),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
