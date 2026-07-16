'use client'
import { Card } from 'react-bootstrap'
import { useStreamReport } from '@/hooks/stream/report/useStreamReportQuery'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import StreamReportPresentation, { hasReportContent } from './StreamReportPresentation'

const ReportShell = ({ children }) => (
    <Card className="stream-report">
        <Card.Body>
            <h3 className="section-label mb-3">Report card</h3>
            {children}
        </Card.Body>
    </Card>
)

const StreamReportCard = ({ streamId }) => {
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useStreamReport(streamId)

    if (isLoading) {
        return (
            <ReportShell>
                <LoadingSpinner size="md" text="Loading report..." />
            </ReportShell>
        )
    }
    if (error) {
        return (
            <ReportShell>
                <ErrorAlert
                    error={error}
                    title="Failed to load report"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            </ReportShell>
        )
    }
    if (!hasReportContent(data)) {
        return (
            <ReportShell>
                <p className="stat-hint text-muted mb-0">
                    Metrics not yet computed for this stream.
                </p>
            </ReportShell>
        )
    }
    return (
        <ReportShell>
            <StreamReportPresentation data={data} />
        </ReportShell>
    )
}

export default StreamReportCard
