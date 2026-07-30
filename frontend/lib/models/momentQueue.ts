export type MomentReviewStatus = 'bookmarked' | 'rejected' | 'clipped' | 'published'

export interface MomentPhrase { phrase: string, count: number }
export interface MomentSampleMessage { text: string, count: number }

export interface MomentsQueueRequest {
    status?: 'pending' | MomentReviewStatus
    creatorId?: number
    pageSize?: number
    rowOffset?: number
}

export interface SetMomentReviewCommand {
    action: 'set'
    streamId: number
    bucketMinute: string
    status: MomentReviewStatus
    /** null explicitly clears the clip URL */
    clipUrl?: string | null
    /** null explicitly clears the curator note */
    note?: string | null
}

export interface ClearMomentReviewCommand {
    action: 'clear'
    streamId: number
    bucketMinute: string
}

export type MomentReviewCommand = SetMomentReviewCommand | ClearMomentReviewCommand

export interface MomentReviewResult {
    status: MomentReviewStatus | null
    clipUrl: string | null
    note: string | null
    updatedAt: string | null
}

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
