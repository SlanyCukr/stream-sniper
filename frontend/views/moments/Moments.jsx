'use client'
import MomentFilters from '@/components/moments/MomentFilters'
import MomentQueue from '@/components/moments/MomentQueue'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import CreatorLoadError from '@/components/creator/CreatorLoadError'
import { useMomentsController } from '@/hooks/moments/useMomentsController'

const Moments = () => {
    const {
        creatorsQuery,
        queueState,
        filterProps,
        queueProps,
    } = useMomentsController()

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">chat spikes worth clipping</p>
                    <h1 className="page-title">Highlights</h1>
                </div>
            </div>

            <CreatorLoadError query={creatorsQuery} />

            <MomentFilters {...filterProps} />

            {queueState.error ? (
                <ErrorAlert
                    error={queueState.error}
                    title="Failed to load highlight queue"
                    onRetry={queueState.refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : queueState.isLoading ? (
                <LoadingSpinner text="Loading highlight queue..." centered />
            ) : (
                <MomentQueue {...queueProps} />
            )}
        </>
    )
}

export default Moments
