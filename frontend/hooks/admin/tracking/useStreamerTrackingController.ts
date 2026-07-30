import { useState } from 'react'
import { usePagedFilters } from '@/hooks/usePagedFilters'
import { useStreamerTrackingActions } from './useStreamerTrackingActions'
import { useTrackedStreamers, type TrackedStreamer } from './useTrackingQueries'

const PAGE_SIZE = 20

interface StreamerFilterState {
    isActive: boolean | null
    processingEnabled: boolean | null
}

export const useStreamerTrackingController = () => {
    const [showAddModal, setShowAddModal] = useState(false)
    const [removeTarget, setRemoveTarget] = useState<TrackedStreamer | null>(null)
    const {
        pageIndex, setPageIndex, filters, setFilter, retreatPage,
    } = usePagedFilters<StreamerFilterState>({
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

    const handleFilterChange = setFilter

    const handleRemoveStreamer = async (streamerId: number) => {
        const outcome = await actions.commands.removeStreamer(streamerId)
        if (!outcome.ok) return outcome
        if (streamers.length === 1) {
            retreatPage()
        }
        setRemoveTarget(null)
        return outcome
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
            onProbe: actions.commands.probeChannel,
            probeResults: actions.probe.results,
            probingId: actions.probe.probingId,
        },
        addModalProps: {
            show: showAddModal,
            pending: actions.pending.create,
            onHide: () => setShowAddModal(false),
            onCreate: actions.commands.addStreamer,
        },
        removeModalProps: {
            target: removeTarget,
            pending: actions.pending.delete,
            onHide: () => setRemoveTarget(null),
            onConfirm: handleRemoveStreamer,
        },
        feedback: actions.feedback,
        openAddModal: () => setShowAddModal(true),
    }
}
