import { useQuery } from '@tanstack/react-query'
import { retrieveAudienceMovement } from '@/lib/api/creators'
import {
    requireArrayField, requireRecord,
} from '@/lib/api/contractGuards'

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

export const useAudienceMovement = (
    creatorId,
    { days = 30 } = {},
    { enabled = true, ...options } = {},
) => useQuery({
    ...options,
    queryKey: audienceMovementKeys.detail(creatorId, days),
    queryFn: async () => {
        const { data: value } = await retrieveAudienceMovement(creatorId, days)
        const data = requireRecord(value, 'audience movement')
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
            priorChannelsForGained: requireArrayField(
                data, 'prior_channels_for_gained', 'audience movement',
            ).map(mapAssociation),
            currentChannelsForLapsed: requireArrayField(
                data, 'current_channels_for_lapsed', 'audience movement',
            ).map(mapAssociation),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
