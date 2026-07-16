import { useCallback, useState } from 'react'
import { useStreamerTrackingActions } from './useStreamerTrackingActions'
import { useTrackedStreamers } from './useTrackingQueries'

const PAGE_SIZE = 20

export const useStreamerTrackingController = () => {
    const [showAddModal, setShowAddModal] = useState(false)
    const [removeTarget, setRemoveTarget] = useState(null)
    const [pageIndex, setPageIndex] = useState(0)
    const [filters, setFilters] = useState({
        isActive: null,
        processingEnabled: null,
    })
    const {
        data: streamersData,
        error: streamersError,
        isPending: loading,
        refetch: refetchStreamers,
    } = useTrackedStreamers({
        pageIndex,
        pageSize: PAGE_SIZE,
        ...filters,
    })
    const streamers = streamersData?.items || []
    const total = streamersData?.total || 0
    const pageCount = streamersData?.pageCount || 0
    const actions = useStreamerTrackingActions()

    const handleFilterChange = useCallback((key, value) => {
        setFilters(current => ({
            ...current,
            [key]: value,
        }))
        setPageIndex(0)
    }, [])

    const handleRemoveStreamer = async streamerId => {
        const succeeded = await actions.commands.removeStreamer(streamerId)
        if (succeeded && streamers.length === 1) {
            setPageIndex(current => Math.max(current - 1, 0))
        }
        setRemoveTarget(null)
        return succeeded
    }

    return {
        queryState: {
            error: streamersError,
            isLoading: loading,
            refetch: refetchStreamers,
        },
        filterProps: {
            filters,
            total,
            onChange: handleFilterChange,
        },
        tableProps: {
            streamers,
            total,
            loading,
            pageIndex,
            pageCount,
            updatePending: actions.pending.update,
            deletePending: actions.pending.delete,
            onPageChange: setPageIndex,
            onToggleActive: actions.commands.toggleActive,
            onToggleProcessing: actions.commands.toggleProcessing,
            onRemove: setRemoveTarget,
        },
        addModalProps: {
            show: showAddModal,
            onHide: () => setShowAddModal(false),
            onCreate: actions.commands.addStreamer,
        },
        removeModalProps: {
            target: removeTarget,
            onHide: () => setRemoveTarget(null),
            onConfirm: handleRemoveStreamer,
        },
        feedback: actions.feedback,
        openAddModal: () => setShowAddModal(true),
    }
}
