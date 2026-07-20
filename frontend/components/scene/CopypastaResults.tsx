import CopypastaCard from './CopypastaCard'
import Pagination from '@/components/common/pagination/Pagination'
import QueryState from '@/components/common/QueryState'
import type { useSceneCopypastas } from '@/hooks/scene/useSceneCopypastaQueries'

interface CopypastaResultsProps {
    query: ReturnType<typeof useSceneCopypastas>
    pageIndex: number
    onPageChange: (pageIndex: number) => void
}

const CopypastaResults = ({
    query, pageIndex, onPageChange,
}: CopypastaResultsProps) => (
    <QueryState
        query={query}
        loadingSize="md"
        loadingText="Loading copypasta..."
        errorTitle="Failed to load copypasta library"
        isEmpty={data => (data.items || []).length === 0}
        emptyState={(
            <div className="empty-state">
                <span className="empty-scope" aria-hidden="true" />
                <p className="empty-title">No copypasta yet</p>
                <p className="empty-hint">
                    No copypasta matches this filter yet. Entries appear after
                    streams are processed.
                </p>
            </div>
        )}
    >
        {data => (
            <>
                <div
                    className={`pasta-list${query.isPlaceholderData ? ' is-refetching' : ''}`}
                    aria-busy={query.isPlaceholderData}
                >
                    {(data.items || []).map(pasta => <CopypastaCard key={pasta.messageTextId} pasta={pasta} />)}
                </div>
                <Pagination
                    pageIndex={pageIndex}
                    pageCount={data.pageCount || 0}
                    onPageChange={onPageChange}
                    ariaLabel="Copypasta pagination"
                />
            </>
        )}
    </QueryState>
)

export default CopypastaResults
