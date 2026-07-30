'use client'
import { Button } from 'react-bootstrap'
import ActionFeedback from '@/components/admin/ActionFeedback'
import AddTrackedStreamerModal from '@/components/admin/tracking/streamers/AddTrackedStreamerModal'
import RemoveTrackedStreamerModal from '@/components/admin/tracking/streamers/RemoveTrackedStreamerModal'
import TrackedStreamerFilters from '@/components/admin/tracking/streamers/TrackedStreamerFilters'
import TrackedStreamerTable from '@/components/admin/tracking/streamers/TrackedStreamerTable'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import { useStreamerTrackingController } from '@/hooks/admin/tracking/useStreamerTrackingController'

const StreamerTracking = () => {
    const {
        queryState,
        filterProps,
        tableProps,
        addModalProps,
        removeModalProps,
        feedback,
        openAddModal,
    } = useStreamerTrackingController()

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Streamer tracking</h1>
                    <p className="page-sub">Automated VOD collection targets</p>
                </div>
                <div className="page-actions">
                    <Button
                        variant="primary"
                        onClick={openAddModal}
                        disabled={queryState.isLoading}
                    >
                        <i
                            className="bi bi-plus-circle me-2"
                            aria-hidden="true" />
                        Add streamer
                    </Button>
                </div>
            </div>

            <ErrorAlert
                error={queryState.error}
                title="Tracked streamers unavailable"
                onRetry={queryState.refetch}
                className="mb-4" />

            <ActionFeedback feedback={feedback} />

            <TrackedStreamerFilters {...filterProps} />
            <TrackedStreamerTable {...tableProps} />
            <AddTrackedStreamerModal {...addModalProps} />
            <RemoveTrackedStreamerModal {...removeModalProps} />
        </>
    )
}

export default StreamerTracking
