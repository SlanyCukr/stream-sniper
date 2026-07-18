'use client'

import StatusChip from '@/components/common/StatusChip'

export interface ArchetypeBadge {
    key: string
    label: string
    description: string
}

/**
 * Renders the passport's rule-based identity badges as a row of neutral status
 * chips (label visible, reason in the tooltip). Honest badges only — these are
 * exactly what the API returns (loyalist / wanderer / marathoner / ...); nothing
 * is derived client-side. Renders nothing when no badge applies.
 */
const ArchetypeBadges = ({ archetypes }: { archetypes: ArchetypeBadge[] }) => {
    if (archetypes.length === 0) return null
    return (
        <>
            {archetypes.map(badge => (
                // Wrap in a span (mirrors the BOT chip) so the native title tooltip
                // and aria-label attach — StatusChip's prop type declares neither.
                <span
                    key={badge.key}
                    title={badge.description}
                    aria-label={`${badge.label}: ${badge.description}`}
                >
                    <StatusChip variant="neutral">{badge.label}</StatusChip>
                </span>
            ))}
        </>
    )
}

export default ArchetypeBadges
