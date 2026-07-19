'use client'
import MomentFilters from '@/components/moments/MomentFilters'
import MomentQueue from '@/components/moments/MomentQueue'
import QueryState from '@/components/common/QueryState'
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
                    <h1 className="page-title">Moments</h1>
                </div>
            </div>

            <CreatorLoadError query={creatorsQuery} />

            <MomentFilters {...filterProps} />

            <QueryState
                query={{
                    error: queueState.error,
                    isLoading: queueState.isLoading,
                    refetch: queueState.refetch,
                    data: !queueState.isLoading && !queueState.error ? queueProps.items : undefined,
                }}
                errorTitle="Failed to load highlight queue"
                loadingText="Loading highlight queue..."
                loadingSize="md"
            >
                {() => <MomentQueue {...queueProps} />}
            </QueryState>
        </>
    )
}

export default Moments
