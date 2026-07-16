import {
    Col, Row,
} from 'react-bootstrap'
import ProcessingJobsStatistics from '@/components/admin/tracking/jobs/ProcessingJobsStatistics'
import ProcessingOverviewCard from './ProcessingOverviewCard'
import SystemStatusCard from '@/components/admin/system/SystemStatusCard'
import TrackedStreamersCard from './TrackedStreamersCard'
import TrackingDashboardActions from './TrackingDashboardActions'

/** @typedef {ReturnType<typeof import('@/hooks/admin/tracking/useTrackingQueries').mapTrackingStats>} TrackingStats */

/** @param {{stats:TrackingStats, onRefresh:()=>unknown, loading:boolean}} props */
const TrackingDashboardContent = ({
    stats, onRefresh, loading,
}) => (
    <>
        <Row className="mb-4">
            <Col md={4}><SystemStatusCard stats={stats} /></Col>
            <Col md={4}><TrackedStreamersCard stats={stats} /></Col>
            <Col md={4}><ProcessingOverviewCard stats={stats} /></Col>
        </Row>
        <Row className="mb-4">
            <Col><ProcessingJobsStatistics processingStats={stats.processingJobs} /></Col>
        </Row>
        <TrackingDashboardActions stats={stats} fetchStats={onRefresh} loading={loading} />
    </>
)

export default TrackingDashboardContent
