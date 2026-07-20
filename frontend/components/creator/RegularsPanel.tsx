'use client'
import {
    useCallback, useState, type ChangeEvent,
} from 'react'
import { Card } from 'react-bootstrap'
import { useCreatorRegulars } from '@/hooks/creator/useCreatorRegularsQuery'
import {
    DEFAULT_MIN_STREAMS, MIN_STREAMS_MAX, MIN_STREAMS_MIN,
} from '@/lib/creator/config'
import QueryState from '@/components/common/QueryState'
import { useTableSort, type SortDirection } from '@/hooks/useTableSort'
import CreatorPanelEmpty from './CreatorPanelEmpty'
import RegularsTable, { RegularsControls } from './RegularsPresentation'

const defaultSortDirection = (): SortDirection => 'desc'

interface RegularsPanelProps {
    creatorId: number | null
}

const RegularsPanel = ({ creatorId }: RegularsPanelProps) => {
    const { sort, dir, onSort } = useTableSort<string>({
        initialKey: 'attendance',
        initialDirection: 'desc',
        getDefaultDirection: defaultSortDirection,
    })
    const [minStreams, setMinStreams] = useState(DEFAULT_MIN_STREAMS)
    // useCreatorRegulars requires a number; the query is `enabled: Boolean(creatorId)`
    // internally, so a null creatorId here never actually fires a request.
    const query = useCreatorRegulars(creatorId as number, {
        minStreams,
        sort,
        dir,
        limit: 50,
    })
    const regulars = query.data?.regulars || []
    const totalStreams = query.data?.totalStreams || 0

    const handleMinStreamsChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
        const value = Number.parseInt(event.target.value, 10)
        setMinStreams(Number.isNaN(value)
            ? MIN_STREAMS_MIN
            : Math.min(MIN_STREAMS_MAX, Math.max(MIN_STREAMS_MIN, value)))
    }, [])

    if (!creatorId) {
        return (
            <CreatorPanelEmpty title="No creator selected">
                Select a creator to see their most loyal chatters across all captured streams.
            </CreatorPanelEmpty>
        )
    }

    return (
        <>
            <RegularsControls
                minStreams={minStreams}
                onMinStreamsChange={handleMinStreamsChange}
                regularCount={regulars.length}
                totalStreams={totalStreams}
                showReadout={!query.isLoading && !query.error}
            />
            <Card>
                <Card.Body className={regulars.length === 0 ? 'p-0' : ''}>
                    <QueryState
                        query={query}
                        errorTitle="Failed to load regulars"
                        loadingText="Loading regulars..."
                        isEmpty={data => data.regulars.length === 0}
                        emptyState={(
                            <div className="empty-state">
                                <div className="empty-scope" aria-hidden="true" />
                                <p className="empty-title">No regulars found</p>
                                <p className="empty-hint">
                                    No chatters attended at least {minStreams} stream{minStreams === 1 ? '' : 's'} for this creator.
                                </p>
                            </div>
                        )}
                    >
                        {data => (
                            <RegularsTable
                                regulars={data.regulars}
                                totalStreams={data.totalStreams || 0}
                                sort={sort}
                                dir={dir}
                                onSort={onSort}
                            />
                        )}
                    </QueryState>
                </Card.Body>
            </Card>
        </>
    )
}

export default RegularsPanel
