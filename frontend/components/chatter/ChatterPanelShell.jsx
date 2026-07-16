import { Card } from 'react-bootstrap'
import EmptyState from '@/components/common/EmptyState'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const ChatterPanelShell = ({
    chatter,
    itemCount,
    summaryCount,
    summaryUnit,
    isLoading,
    error,
    onRetry,
    loadingText,
    errorTitle,
    awaitingHint,
    emptyTitle,
    emptyHint,
    regionLabel,
    children,
}) => {
    const chatterId = chatter?.value || null
    return (
        <>
            {chatter && summaryCount > 0 && !isLoading ? (
                <div className="d-flex justify-content-end mb-2">
                    <span className="toolbar-readout">
                        <strong>{summaryCount.toLocaleString()}</strong> {summaryUnit} · target <strong>{chatter.label}</strong>
                    </span>
                </div>
            ) : null}
            <Card>
                <Card.Body className={!chatter || (chatterId && itemCount === 0 && !isLoading) ? 'p-0' : ''}>
                    {!chatter ? <EmptyState title="Awaiting target">{awaitingHint}</EmptyState> : null}
                    {isLoading ? <LoadingSpinner size="lg" text={loadingText} /> : null}
                    {error && !isLoading ? (
                        <ErrorAlert
                            error={error}
                            title={errorTitle}
                            onRetry={onRetry}
                            showDetails={process.env.NODE_ENV === 'development'}
                        />
                    ) : null}
                    {chatterId && !isLoading && !error ? (
                        <div role="region" aria-label={regionLabel} aria-live="polite">
                            {itemCount === 0
                                ? <EmptyState title={emptyTitle}>{emptyHint}</EmptyState>
                                : children}
                        </div>
                    ) : null}
                </Card.Body>
            </Card>
        </>
    )
}

export default ChatterPanelShell
