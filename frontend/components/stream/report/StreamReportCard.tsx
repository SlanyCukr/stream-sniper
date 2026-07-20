'use client'
import { Card } from 'react-bootstrap'
import { useStreamReport } from '@/hooks/stream/report/useStreamReportQuery'
import QueryState from '@/components/common/QueryState'
import StreamReportPresentation, { hasReportContent } from './StreamReportPresentation'

interface StreamReportCardProps {
    streamId: number
}

const StreamReportCard = ({ streamId }: StreamReportCardProps) => {
    const query = useStreamReport(streamId)

    return (
        <Card className="stream-report">
            <Card.Body>
                <h3 className="section-label mb-3">Report card</h3>
                <QueryState
                    query={query}
                    loadingSize="md"
                    loadingText="Loading report..."
                    errorTitle="Failed to load report"
                    isEmpty={data => !hasReportContent(data)}
                    emptyState={(
                        <p className="stat-hint text-muted mb-0">
                            Metrics not yet computed for this stream.
                        </p>
                    )}
                >
                    {data => <StreamReportPresentation data={data} />}
                </QueryState>
            </Card.Body>
        </Card>
    )
}

export default StreamReportCard
