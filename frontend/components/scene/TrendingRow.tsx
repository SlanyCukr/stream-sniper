'use client'

import Link from 'next/link'
import type { CSSProperties } from 'react'
import StatusChip from '@/components/common/StatusChip'
import {
    trendIndicator,
    type TrendingRowModel,
} from '@/components/scene/trending/presentationModel'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'

interface TrendingRowProps {
    rank: number
    row: TrendingRowModel
    maxUsage: number
}

const TrendingRow = ({ rank, row, maxUsage }: TrendingRowProps) => {
    const indicator = trendIndicator(row.trend, row.deltaPct)
    const barStyle: CSSProperties = { width: `${magnitudeBarWidth(row.currentUsage, maxUsage)}%` }

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
