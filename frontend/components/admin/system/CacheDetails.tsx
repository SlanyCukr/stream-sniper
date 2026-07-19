'use client'
import {
    Row, Col, Card,
} from 'react-bootstrap'
import type { CacheStats } from '@/hooks/admin/system/useSystemQueries'

interface CacheDetailsProps {
    cacheStats: CacheStats
}

const CacheDetails = ({
    cacheStats,
}: CacheDetailsProps) => (
    <Row className="mb-4">
        <Col>
            <Card>
                <Card.Body>
                    <h3 className="section-label mb-3">Cache</h3>
                    <dl className="spec-list">
                        <dt>Backend</dt>
                        <dd className="mono">{cacheStats.backend}</dd>
                        <dt>Status</dt>
                        <dd className="mono">{cacheStats.status}</dd>
                        <dt>Cached keys</dt>
                        <dd className="mono">{cacheStats.streamSniperKeys}</dd>
                    </dl>
                </Card.Body>
            </Card>
        </Col>
    </Row>
)

export default CacheDetails
