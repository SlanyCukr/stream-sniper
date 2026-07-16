import { Card } from 'react-bootstrap'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const StreamInsightPanel = ({
    title,
    query,
    hasItems,
    loadingText,
    errorTitle,
    emptyTitle,
    emptyHint,
    children,
}) => (
    <Card className="insight-panel">
        <Card.Body>
            <h3 className="section-label mb-3">{title}</h3>
            {query.isLoading ? <LoadingSpinner size="md" text={loadingText} /> : null}
            {query.error && !query.isLoading ? (
                <ErrorAlert
                    error={query.error}
                    title={errorTitle}
                    onRetry={query.refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : null}
            {!query.isLoading && !query.error && !hasItems ? (
                <div className="empty-state">
                    <div className="empty-scope" aria-hidden="true" />
                    <p className="empty-title">{emptyTitle}</p>
                    <p className="empty-hint">{emptyHint}</p>
                </div>
            ) : null}
            {!query.isLoading && !query.error && hasItems ? children : null}
        </Card.Body>
    </Card>
)

export default StreamInsightPanel
