import type { StatusChipVariant } from '@/components/common/StatusChip'

/** A single magnitude/context pair rendered as a muted chip (e.g. "4 streams"). */
export interface TrendingContext {
    label: string
    value: number
}

/** Presentation-normalized shape shared by trending producers and renderers. */
export interface TrendingRowModel {
    key: string
    label: string
    href: string | null
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

export const formatDeltaPct = (value: number | null): string => {
    if (value === null || !Number.isFinite(value)) return '—'
    return `${value > 0 ? '+' : ''}${value}%`
}

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
