import { useState } from 'react'
import { keepPreviousData } from '@tanstack/react-query'
import {
    mapCreatorOption, useCreators,
} from '@/hooks/creator/useCreatorsQuery'
import {
    useMomentReview, useMomentsQueue,
} from './useMomentsQueries'
import { useAuth } from '@/contexts/AuthContext'
import { PAGINATION } from '@/lib/pagination/constants'
import { MOMENT_STATUS_TABS } from '@/lib/models/momentQueue'

export const useMomentsController = () => {
    const { isAdmin } = useAuth()
    const [statusKey, setStatusKey] = useState('all')
    const [selectedCreator, setSelectedCreator] = useState(null)
    const [pageIndex, setPageIndex] = useState(0)
    const [reviewFailure, setReviewFailure] = useState(null)
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

    const handleStatusChange = nextStatus => {
        setStatusKey(nextStatus)
        setPageIndex(0)
    }

    const handleCreatorChange = creator => {
        setSelectedCreator(creator)
        setPageIndex(0)
    }

    const handleReview = async (moment, nextStatus, metadata = {}) => {
        const target = { streamId: moment.streamId, bucketMinute: moment.t }
        const key = `${target.streamId}:${target.bucketMinute}`
        setReviewFailure(current => current?.key === key ? null : current)
        const command = nextStatus === null
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
            setReviewFailure(current => current?.key === key ? null : current)
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
