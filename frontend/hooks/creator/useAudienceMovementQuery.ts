import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveAudienceMovement,
    type AudienceAssociationDto,
    type AudienceMovementDto,
} from '@/lib/api/creators'
import {
    requireArrayField, requireRecord,
} from '@/lib/api/contractGuards'

export interface AudienceAssociation {
    creatorId: number
    nick: string
    displayName: string
    chatterCount: number
}

export interface AudienceMovement {
    creatorId: number
    windowDays: number
    currentAudience: number
    previousAudience: number
    retained: number
    gained: number
    lapsed: number
    retentionRate: number | null
    gainRate: number | null
    priorChannelsForGained: AudienceAssociation[]
    currentChannelsForLapsed: AudienceAssociation[]
}

type QueryOptions = Omit<
    UseQueryOptions<AudienceMovement, Error, AudienceMovement, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

export const audienceMovementKeys = {
    all: ['audience-movement'],
    detail: (creatorId: number, days: number) => [...audienceMovementKeys.all, { creatorId, days }],
}

const mapAssociation = (item: AudienceAssociationDto): AudienceAssociation => ({
    creatorId: item.creator_id,
    nick: item.nick,
    displayName: item.display_name,
    chatterCount: item.chatter_count,
})

export const useAudienceMovement = (
    creatorId: number,
    { days = 30 }: { days?: number } = {},
    { enabled = true, ...options }: QueryOptions & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: audienceMovementKeys.detail(creatorId, days),
    queryFn: async () => {
        const { data: value } = await retrieveAudienceMovement(creatorId, days)
        const record = requireRecord(value, 'audience movement')
        // requireRecord only checks the value is a plain object; individual fields
        // are trusted against the wire DTO rather than guarded field-by-field
        // (matches existing behavior).
        const data = record as unknown as AudienceMovementDto
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
                record, 'prior_channels_for_gained', 'audience movement',
            ).map(item => mapAssociation(item as AudienceAssociationDto)),
            currentChannelsForLapsed: requireArrayField(
                record, 'current_channels_for_lapsed', 'audience movement',
            ).map(item => mapAssociation(item as AudienceAssociationDto)),
        }
    },
    enabled: Boolean(creatorId) && enabled,
})
