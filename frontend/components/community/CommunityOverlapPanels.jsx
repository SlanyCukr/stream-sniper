'use client'
import {
    useState,
} from 'react'
import { Card } from 'react-bootstrap'
import { useOverlapModel } from '@/hooks/community/useOverlapModel'
import OverlapMatrix from './OverlapMatrix'
import OverlapTable from './OverlapTable'
import NeighborsExplorer from './NeighborsExplorer'

const formatJaccard = value => (value == null ? '--' : `${(value * 100).toFixed(1)}%`)

const OverlapDetail = ({ detail }) => {
    if (!detail) return null
    return (
        <div className="overlap-detail">
            <span className="overlap-detail-pair">
                {detail.aName} <span aria-hidden="true">×</span> {detail.bName}
            </span>
            {[
                ['shared chatters', detail.sharedChatters.toLocaleString()],
                ['shared regulars', detail.sharedRegulars.toLocaleString()],
                ['jaccard chatters', formatJaccard(detail.jaccardChatters)],
                ['jaccard regulars', formatJaccard(detail.jaccardRegulars)],
            ].map(([label, value]) => (
                <span className="overlap-detail-metric" key={label}>
                    <span className="overlap-detail-key">{label}</span>
                    <span className="mono">{value}</span>
                </span>
            ))}
        </div>
    )
}

const CommunityOverlapPanels = ({
    creators,
    pairs,
    metric,
    selectedPair,
    onSelectPair,
    isRefetching,
}) => {
    const [selectedCreator, setSelectedCreator] = useState(null)
    const overlap = useOverlapModel({
        creators, pairs, metric, selectedPair, onSelectPair,
    })

    return (
        <div className={isRefetching ? 'community-grid is-refetching' : 'community-grid'}>
            <Card><Card.Body>
                <span className="section-label">Overlap matrix</span>
                <OverlapMatrix
                    creators={creators}
                    metric={metric}
                    model={overlap.matrix}
                />
                <OverlapDetail detail={overlap.detail} />
            </Card.Body></Card>

            <Card><Card.Body>
                <span className="section-label">Overlap pairs</span>
                <OverlapTable
                    model={overlap.table}
                />
            </Card.Body></Card>

            <Card><Card.Body>
                <span className="section-label">Audience also watches</span>
                <NeighborsExplorer
                    creators={creators}
                    metric={metric}
                    selected={selectedCreator}
                    onSelect={setSelectedCreator}
                />
            </Card.Body></Card>
        </div>
    )
}

export default CommunityOverlapPanels
