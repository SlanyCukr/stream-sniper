import type { ReactNode } from 'react'
import { Card } from 'react-bootstrap'
import QueryState from '@/components/common/QueryState'

interface StreamInsightQuery<TData> {
    data?: TData
    isLoading: boolean
    error: Error | null
    refetch: () => unknown
}

interface StreamInsightPanelProps<TData> {
    title: string
    query: StreamInsightQuery<TData>
    /** Predicate deciding the empty slot (rollup not yet run / nothing found). */
    isEmpty: (data: TData) => boolean
    loadingText: string
    errorTitle: string
    emptyTitle: string
    emptyHint: string
    /** Render prop for resolved data, per the QueryState convention. */
    children: (data: TData) => ReactNode
}

/**
 * Titled insight card whose loading / error / empty / content branching is
 * delegated to QueryState (single policy: stale non-empty data survives a
 * transient refetch error instead of being blanked by it).
 */
const StreamInsightPanel = <TData,>({
    title,
    query,
    isEmpty,
    loadingText,
    errorTitle,
    emptyTitle,
    emptyHint,
    children,
}: StreamInsightPanelProps<TData>) => (
    <Card className="insight-panel">
        <Card.Body>
            <h3 className="section-label mb-3">{title}</h3>
            <QueryState
                query={query}
                loadingSize="md"
                loadingText={loadingText}
                errorTitle={errorTitle}
                isEmpty={isEmpty}
                emptyState={(
                    <div className="empty-state">
                        <div className="empty-scope" aria-hidden="true" />
                        <p className="empty-title">{emptyTitle}</p>
                        <p className="empty-hint">{emptyHint}</p>
                    </div>
                )}
            >
                {children}
            </QueryState>
        </Card.Body>
    </Card>
)

export default StreamInsightPanel
