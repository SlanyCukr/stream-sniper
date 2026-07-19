'use client'
import {
    useCallback, useState, type ChangeEvent,
} from 'react'
import { Card } from 'react-bootstrap'
import { useCreatorRegulars } from '@/hooks/creator/useCreatorRegularsQuery'
import {
    DEFAULT_MIN_STREAMS, MIN_STREAMS_MAX, MIN_STREAMS_MIN,
} from '@/lib/creator/config'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
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
                <Card.Body className={query.isLoading || query.error || regulars.length === 0 ? 'p-0' : ''}>
                    {query.isLoading ? <LoadingSpinner size="lg" text="Loading regulars..." /> : null}
                    {query.error ? (
                        <ErrorAlert
                            error={query.error}
                            title="Failed to load regulars"
                            onRetry={query.refetch}
                            showDetails={process.env.NODE_ENV === 'development'}
                        />
                    ) : null}
                    {!query.isLoading && !query.error && regulars.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-scope" aria-hidden="true" />
                            <p className="empty-title">No regulars found</p>
                            <p className="empty-hint">
                                No chatters attended at least {minStreams} stream{minStreams === 1 ? '' : 's'} for this creator.
                            </p>
                        </div>
                    ) : null}
                    {!query.isLoading && !query.error && regulars.length > 0 ? (
                        <RegularsTable
                            regulars={regulars}
                            totalStreams={totalStreams}
                            sort={sort}
                            dir={dir}
                            onSort={onSort}
                        />
                    ) : null}
                </Card.Body>
            </Card>
        </>
    )
}

export default RegularsPanel
