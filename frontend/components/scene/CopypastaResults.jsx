import CopypastaCard from './CopypastaCard'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import Pagination from '@/components/common/pagination/Pagination'

const CopypastaResults = ({
    query, pageIndex, onPageChange,
}) => {
    const items = query.data?.items || []

    if (query.error) {
        return (
            <ErrorAlert
                error={query.error}
                title="Failed to load copypasta library"
                onRetry={query.refetch}
                showDetails={process.env.NODE_ENV === 'development'}
            />
        )
    }
    if (query.isLoading) return <LoadingSpinner text="Loading copypasta..." centered />
    if (items.length === 0) {
        return (
            <div className="empty-state">
                <span className="empty-scope" aria-hidden="true" />
                <p className="empty-title">No copypasta yet</p>
                <p className="empty-hint">
                    No copypasta matches this filter yet. Entries appear after
                    streams are processed.
                </p>
            </div>
        )
    }

    return (
        <>
            <div
                className={`pasta-list${query.isPlaceholderData ? ' is-refetching' : ''}`}
                aria-busy={query.isPlaceholderData}
            >
                {items.map(pasta => <CopypastaCard key={pasta.messageTextId} pasta={pasta} />)}
            </div>
            <Pagination
                pageIndex={pageIndex}
                pageCount={query.data?.pageCount || 0}
                onPageChange={onPageChange}
                ariaLabel="Copypasta pagination"
            />
        </>
    )
}

export default CopypastaResults
