import type { UseQueryResult } from '@tanstack/react-query'
import Link from 'next/link'
import EmptyState from '@/components/common/EmptyState'
import QueryState from '@/components/common/QueryState'
import type { CreatorNeighbors, OverlapMetric } from '@/hooks/community/useCommunityQuery'
import type { NeighborWithShared } from '@/hooks/community/useNeighborsExplorerModel'

interface NeighborResultsProps {
    creatorId: number | null
    query: UseQueryResult<CreatorNeighbors, Error>
    neighbors: NeighborWithShared[]
    metric: OverlapMetric
    maxShared: number
}

const NeighborResults = ({
    creatorId, query, neighbors, metric, maxShared,
}: NeighborResultsProps) => {
    if (!creatorId) {
        return <EmptyState title="No creator selected">Pick a creator to rank the channels their audience also watches.</EmptyState>
    }

    return (
        <QueryState
            query={query}
            loadingText="Loading neighbors..."
            errorTitle="Failed to load neighbors"
            isEmpty={() => neighbors.length === 0}
            emptyState={(
                <EmptyState title="No shared audience">
                    No overlapping {metric} recorded with other tracked creators yet.
                </EmptyState>
            )}
        >
            {() => (
                <ol className="rank-list neighbors-rank">
                    {neighbors.map((neighbor, index) => (
                        <li key={neighbor.creatorId}>
                            <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                            <Link className="nick" href={`/creator/${neighbor.creatorId}`}>
                                {neighbor.displayName || neighbor.nick || `#${neighbor.creatorId}`}
                            </Link>
                            <span className="neighbors-bar-wrap">
                                <span className="data-bar" aria-hidden="true">
                                    <span
                                        className="data-bar-fill"
                                        style={{ width: `${Math.max(4, Math.round(((neighbor.shared || 0) / maxShared) * 100))}%` }}
                                    />
                                </span>
                            </span>
                            <span className="count">{(neighbor.shared || 0).toLocaleString()}</span>
                        </li>
                    ))}
                </ol>
            )}
        </QueryState>
    )
}

export default NeighborResults
