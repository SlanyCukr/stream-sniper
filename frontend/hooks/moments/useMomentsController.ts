import { useState } from 'react'
import { keepPreviousData } from '@tanstack/react-query'
import { usePagedFilters } from '@/hooks/usePagedFilters'
import {
    mapCreatorOption, useCreators, type CreatorOption,
} from '@/hooks/creator/useCreatorsQuery'
import {
    useMomentReview, useMomentsQueue,
    type MomentQueueItem,
} from './useMomentsQueries'
import { useAuth } from '@/contexts/AuthContext'
import { PAGINATION } from '@/lib/pagination/constants'
import {
    MOMENT_STATUS_TABS,
    type MomentReviewCommand,
    type MomentReviewStatus,
} from '@/lib/models/momentQueue'

interface ReviewFailure {
    key: string
    error: unknown
}

interface ReviewMetadata {
    clipUrl?: string | null
    note?: string | null
}

interface MomentFilterState {
    statusKey: string
    selectedCreator: CreatorOption | null
}

export const useMomentsController = () => {
    const { isAdmin } = useAuth()
    const {
        pageIndex, setPageIndex, filters, setFilter,
    } = usePagedFilters<MomentFilterState>({ statusKey: 'all', selectedCreator: null })
    const { statusKey, selectedCreator } = filters
    const [reviewFailure, setReviewFailure] = useState<ReviewFailure | null>(null)
    const status = MOMENT_STATUS_TABS.find(tab => tab.key === statusKey)?.value
    const creatorsQuery = useCreators()
    const creators = creatorsQuery.data?.map(mapCreatorOption) || []
    const queueQuery = useMomentsQueue({
        status,
        creatorId: selectedCreator?.value || undefined,
        pageIndex,
        pageSize: PAGINATION.ITEMS_PER_PAGE,
    }, { placeholderData: keepPreviousData })
    const review = useMomentReview()

    const handleStatusChange = (nextStatus: string) => setFilter('statusKey', nextStatus)
    const handleCreatorChange = (creator: CreatorOption | null) => setFilter('selectedCreator', creator)

    const handleReview = async (
        moment: MomentQueueItem,
        nextStatus: MomentReviewStatus | null,
        metadata: ReviewMetadata = {},
    ) => {
        const target = { streamId: moment.streamId, bucketMinute: moment.t }
        const key = `${target.streamId}:${target.bucketMinute}`
        setReviewFailure(current => (current?.key === key ? null : current))
        const command: MomentReviewCommand = nextStatus === null
            ? { action: 'clear', ...target }
            : {
                action: 'set',
                ...target,
                status: nextStatus,
                clipUrl: metadata.clipUrl ?? null,
                note: metadata.note ?? null,
            }
        try {
            const result = await review.mutateAsync(command)
            setReviewFailure(current => (current?.key === key ? null : current))
            return result
        } catch (error) {
            setReviewFailure({ key, error })
            throw error
        }
    }

    const pendingKey = review.isPending && review.variables
        ? `${review.variables.streamId}:${review.variables.bucketMinute}`
        : null

    return {
        creatorsQuery,
        queueState: {
            error: queueQuery.error,
            isLoading: queueQuery.isLoading,
            refetch: queueQuery.refetch,
        },
        filterProps: {
            statusKey,
            onStatusChange: handleStatusChange,
            creators,
            selectedCreator,
            onCreatorChange: handleCreatorChange,
        },
        queueProps: {
            items: queueQuery.data?.items || [],
            statusKey,
            isPlaceholderData: queueQuery.isPlaceholderData,
            isAdmin,
            pendingKey,
            reviewFailure,
            onDismissReviewError: () => setReviewFailure(null),
            onReview: handleReview,
            pageIndex,
            pageCount: queueQuery.data?.pageCount || 0,
            onPageChange: setPageIndex,
        },
    }
}
