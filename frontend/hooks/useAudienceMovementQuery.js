import { useQuery } from '@tanstack/react-query'
import { retrieveAudienceMovement } from '@/lib/api'

export const audienceMovementKeys = {
    all: ['audience-movement'],
    detail: (creatorId, days) => [...audienceMovementKeys.all, { creatorId, days }],
}

const mapAssociation = item => ({
    creatorId: item.creator_id,
    nick: item.nick,
    displayName: item.display_name,
    chatterCount: item.chatter_count,
})

export const useAudienceMovement = (creatorId, days = 30, options = {}) => useQuery({
    queryKey: audienceMovementKeys.detail(creatorId, days),
    queryFn: async () => {
        const { data = {} } = await retrieveAudienceMovement(creatorId, days)
        return {
            creatorId: data.creator_id,
            windowDays: data.window_days,
            currentAudience: data.current_audience,
            previousAudience: data.previous_audience,
            retained: data.retained,
            gained: data.gained,
            lapsed: data.lapsed,
            retentionRate: data.retention_rate ?? null,
            gainRate: data.gain_rate ?? null,
            priorChannelsForGained: (data.prior_channels_for_gained || []).map(mapAssociation),
            currentChannelsForLapsed: (data.current_channels_for_lapsed || []).map(mapAssociation),
        }
    },
    enabled: Boolean(creatorId),
    ...options,
})
