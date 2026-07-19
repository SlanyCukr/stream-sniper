import type { MomentReviewStatus } from '@/lib/api/moments'

interface MomentStatusTab {
    key: string
    label: string
    value: 'pending' | MomentReviewStatus | undefined
}

export const MOMENT_STATUS_TABS: MomentStatusTab[] = [
    { key: 'all', label: 'All', value: undefined },
    { key: 'pending', label: 'Pending', value: 'pending' },
    { key: 'bookmarked', label: 'Bookmarked', value: 'bookmarked' },
    { key: 'rejected', label: 'Rejected', value: 'rejected' },
    { key: 'clipped', label: 'Clipped', value: 'clipped' },
    { key: 'published', label: 'Published', value: 'published' },
]
