/**
 * Shared contract-guard mappers for the wire shapes every chatter surface
 * receives (passport, versus, scene rankings): the `home_channel` object and
 * the `archetypes` badge list. One mapper each, so validation rules and field
 * names cannot drift between the three hooks that consume them.
 */

import type { ArchetypeBadge } from '@/components/chatter/ArchetypeBadges'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

/** A chatter's dominant channel as the API emits it (null = none dominates). */
export interface ChatterHomeChannel {
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    messages: number
    /** messages / total, rounded server-side to 4 places. */
    share: number
}

/**
 * Map a `home_channel` payload. The API always emits the key (`null` when no
 * channel dominates), so only an explicit `null` maps to null — a missing key
 * is a contract violation.
 */
export const mapHomeChannel = (raw: unknown, label: string): ChatterHomeChannel | null => {
    if (raw === null) return null
    const home = requireRecord(raw, label)
    return {
        creatorId: requireFiniteNumberField(home, 'creator_id', label),
        creatorNick: requireStringField(home, 'creator_nick', label),
        creatorDisplayName: requireStringField(home, 'creator_display_name', label),
        messages: requireFiniteNumberField(home, 'messages', label),
        share: requireFiniteNumberField(home, 'share', label),
    }
}

/** Map a container's `archetypes` array into badge view models. */
export const mapArchetypeBadges = (
    container: Record<string, unknown>,
    label: string,
): ArchetypeBadge[] => (
    requireArrayField(container, 'archetypes', label).map((raw, index) => {
        const badgeLabel = `${label}.archetypes[${index}]`
        const badge = requireRecord(raw, badgeLabel)
        return {
            key: requireStringField(badge, 'key', badgeLabel),
            label: requireStringField(badge, 'label', badgeLabel),
            description: requireStringField(badge, 'description', badgeLabel),
        }
    })
)
