import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveAudienceMovement,
} from '@/lib/api/creators'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { creatorKeys } from './creatorKeys'

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

const mapAssociation = (value: unknown, label: string): AudienceAssociation => {
    const item = requireRecord(value, label)
    return {
        creatorId: requireFiniteNumberField(item, 'creator_id', label),
        nick: requireStringField(item, 'nick', label),
        displayName: requireStringField(item, 'display_name', label),
        chatterCount: requireFiniteNumberField(item, 'chatter_count', label),
    }
}

export const useAudienceMovement = (
    creatorId: number | null,
    { days = 30 }: { days?: number } = {},
    { enabled = true, ...options }: QueryOptions & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: creatorKeys.audienceMovement(creatorId, days),
    queryFn: async () => {
        if (creatorId === null || creatorId <= 0) {
            throw new TypeError('audience movement requires a positive creator ID')
        }
        const value = await retrieveAudienceMovement(creatorId, days)
        const record = requireRecord(value, 'audience movement')
        return {
            creatorId: requireFiniteNumberField(record, 'creator_id', 'audience movement'),
            windowDays: requireFiniteNumberField(record, 'window_days', 'audience movement'),
            currentAudience: requireFiniteNumberField(record, 'current_audience', 'audience movement'),
            previousAudience: requireFiniteNumberField(record, 'previous_audience', 'audience movement'),
            retained: requireFiniteNumberField(record, 'retained', 'audience movement'),
            gained: requireFiniteNumberField(record, 'gained', 'audience movement'),
            lapsed: requireFiniteNumberField(record, 'lapsed', 'audience movement'),
            retentionRate: requireNullableFiniteNumberField(record, 'retention_rate', 'audience movement'),
            gainRate: requireNullableFiniteNumberField(record, 'gain_rate', 'audience movement'),
            priorChannelsForGained: requireArrayField(
                record, 'prior_channels_for_gained', 'audience movement',
            ).map((item, index) => mapAssociation(item, `audience movement.prior_channels_for_gained[${index}]`)),
            currentChannelsForLapsed: requireArrayField(
                record, 'current_channels_for_lapsed', 'audience movement',
            ).map((item, index) => mapAssociation(item, `audience movement.current_channels_for_lapsed[${index}]`)),
        }
    },
    enabled: creatorId !== null && creatorId > 0 && enabled,
})
