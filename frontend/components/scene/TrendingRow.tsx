'use client'

import Link from 'next/link'
import type { CSSProperties } from 'react'
import StatusChip from '@/components/common/StatusChip'
import type { StatusChipVariant } from '@/components/common/StatusChip'
import { formatCompactNumber } from '@/utils/numberUtils'

/** A single magnitude/context pair rendered as a muted chip (e.g. "4 streams"). */
export interface TrendingContext {
    label: string
    value: number
}

/**
 * Presentation-normalized shape both trending boards project into so the row
 * and its data-bar/trend chip stay agnostic to copypasta-vs-emote specifics.
 */
export interface TrendingRowModel {
    key: string
    label: string
    /** Detail link (copypasta trace); null for entities with no dedicated page (emotes). */
    href: string | null
    /** Provider badge shown after the label (emote source); null to omit. */
    source: string | null
    currentUsage: number
    priorUsage: number
    deltaPct: number | null
    trend: string
    context: TrendingContext[]
}

export interface TrendIndicator {
    variant: StatusChipVariant
    label: string
}

/**
 * Sign-aware percent label. delta_pct is already rounded server-side, so it is
 * rendered verbatim (never coerced): null — meaning no prior baseline — becomes
 * an em-dash rather than a misleading "0%".
 */
export const formatDeltaPct = (value: number | null): string => {
    if (value === null || !Number.isFinite(value)) return '—'
    return `${value > 0 ? '+' : ''}${value}%`
}

/**
 * Map a trend classification to a status chip. rising ▲ / falling ▼ carry the
 * signed delta; new and steady (and any unrecognized value) stay neutral so an
 * evolving backend contract degrades gracefully instead of throwing.
 */
export const trendIndicator = (trend: string, deltaPct: number | null): TrendIndicator => {
    switch (trend) {
        case 'rising':
            return { variant: 'ok', label: `▲ ${formatDeltaPct(deltaPct)}` }
        case 'falling':
            return { variant: 'err', label: `▼ ${formatDeltaPct(deltaPct)}` }
        case 'new':
            return { variant: 'neutral', label: 'new' }
        case 'steady':
            return { variant: 'neutral', label: 'steady' }
        default:
            return { variant: 'neutral', label: trend || 'steady' }
    }
}

interface TrendingRowProps {
    rank: number
    row: TrendingRowModel
    maxUsage: number
}

const TrendingRow = ({ rank, row, maxUsage }: TrendingRowProps) => {
    const indicator = trendIndicator(row.trend, row.deltaPct)
    const fillWidth = Math.min(100, Math.max(2, Math.round((row.currentUsage / maxUsage) * 100)))
    const barStyle: CSSProperties = { width: `${fillWidth}%` }

    return (
        <tr>
            <td className="rank-num">{String(rank).padStart(2, '0')}</td>
            <td className="trending-primary">
                {row.href ? (
                    <Link className="trending-label trending-label-link" href={row.href}>
                        {row.label}
                    </Link>
                ) : (
                    <span className="trending-label">{row.label}</span>
                )}
                {row.source ? <span className="trending-source">{row.source}</span> : null}
            </td>
            <td className="trending-usage text-end">
                <span className="mono trending-usage-now">{formatCompactNumber(row.currentUsage)}</span>
                <span className="data-bar" aria-hidden="true">
                    <span className="data-bar-fill" style={barStyle} />
                </span>
                <span className="mono trending-usage-prior">
                    was {formatCompactNumber(row.priorUsage)}
                </span>
            </td>
            <td className="trending-trend">
                <StatusChip variant={indicator.variant}>{indicator.label}</StatusChip>
            </td>
            <td className="trending-context text-end">
                {row.context.map(entry => (
                    <span key={entry.label} className="pasta-chip pasta-chip-muted">
                        {formatCompactNumber(entry.value)}
                        <span className="pasta-chip-unit">{entry.label}</span>
                    </span>
                ))}
            </td>
        </tr>
    )
}

export default TrendingRow
