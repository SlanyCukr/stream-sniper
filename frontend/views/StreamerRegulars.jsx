'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import Select from 'react-select'
import {
    Card, Table,
} from 'react-bootstrap'
import {
    useCreators, useCreatorTopChatters,
} from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

const TOP_CHATTERS_LIMIT = 25

const StreamerRegulars = () => {
    const [
        selectedCreator,
        setSelectedCreator,
    ] = useState(null)

    const {
        data: creatorsData,
        error: creatorsError,
        refetch: refetchCreators,
    } = useCreators()

    const selectedCreatorId = selectedCreator?.value || null

    const {
        data: topChattersData,
        isLoading,
        error,
        refetch,
    } = useCreatorTopChatters(selectedCreatorId, TOP_CHATTERS_LIMIT)

    // Transform creators data for react-select with memoization
    const creators = useMemo(() => creatorsData?.map(creator => ({
        label: creator[1],
        value: creator[0],
    })) || [
    ], [
        creatorsData,
    ])

    const topChatters = useMemo(() => topChattersData || [
    ], [
        topChattersData,
    ])

    // Max message count for relative magnitude bars
    const maxMessages = useMemo(() => Math.max(1, ...topChatters.map(chatter => chatter[2] || 0)), [
        topChatters,
    ])

    /**
     * Handles creator selection change
     * @param {object} selectedOption
     */
    const handleCreatorChange = useCallback(selectedOption => {
        setSelectedCreator(selectedOption)
    }, [
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="regulars-heading" className="page-title">Streamer regulars</h1>
                    <p className="page-sub">Top {TOP_CHATTERS_LIMIT} chatters across all captured streams</p>
                </div>
            </div>

            {creatorsError && (
                <ErrorAlert
                    error={creatorsError}
                    title="Failed to load creators"
                    onRetry={refetchCreators}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}

            <div
                className="toolbar"
                role="search"
                aria-label="Creator selection">
                <span
                    className="toolbar-label"
                    aria-hidden="true">
                    Creator
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="regulars-creator-select"
                        className="visually-hidden"
                    >
                        Select a creator
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="regulars-creator-select"
                        inputId="regulars-creator-select"
                        options={creators}
                        value={selectedCreator}
                        onChange={handleCreatorChange}
                        placeholder="Select creator..."
                        isClearable
                        aria-label="Select a creator to view their regulars"
                    />
                </div>
                {selectedCreatorId && topChatters.length > 0 && !isLoading && (
                    <span className="toolbar-readout">
                        <strong>{topChatters.length}</strong> regulars
                    </span>
                )}
            </div>

            <Card>
                <Card.Body className={!selectedCreatorId || (selectedCreatorId && !isLoading && !error && topChatters.length === 0) ? 'p-0' : ''}>
                    {!selectedCreatorId && (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">No creator selected</p>
                            <p className="empty-hint">
                                Select a creator to see their most loyal chatters across all captured streams.
                            </p>
                        </div>
                    )}

                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Loading regulars..."
                        />
                    )}

                    {error && (
                        <ErrorAlert
                            error={error}
                            title="Failed to load regulars"
                            onRetry={refetch}
                            showDetails={process.env.NODE_ENV === 'development'}
                        />
                    )}

                    {selectedCreatorId && !isLoading && !error && (
                        <div
                            role="region"
                            aria-labelledby="regulars-heading"
                            aria-live="polite"
                        >
                            {topChatters.length === 0
                                ? (
                                    <div className="empty-state">
                                        <div
                                            className="empty-scope"
                                            aria-hidden="true" />
                                        <p className="empty-title">No regulars found</p>
                                        <p className="empty-hint">No chatters recorded for this creator yet.</p>
                                    </div>
                                )
                                : (
                                    <Table
                                        hover
                                        responsive
                                    >
                                        <thead>
                                            <tr>
                                                <th scope="col">#</th>
                                                <th scope="col">Chatter</th>
                                                <th
                                                    scope="col"
                                                    className="text-end">Messages</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {topChatters.map((chatter, index) => (
                                                <tr key={chatter[0]}>
                                                    <td className="rank-num">{String(index + 1).padStart(2, '0')}</td>
                                                    <td>{chatter[1]}</td>
                                                    <td
                                                        className="mono text-end"
                                                        style={{ minWidth: '140px' }}>
                                                        {chatter[2]?.toLocaleString()}
                                                        <span
                                                            className="data-bar"
                                                            aria-hidden="true">
                                                            <span
                                                                className="data-bar-fill"
                                                                style={{ width: `${Math.max(2, Math.round(((chatter[2] || 0) / maxMessages) * 100))}%` }}
                                                            />
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </Table>
                                )}
                        </div>
                    )}
                </Card.Body>
            </Card>
        </>
    )
}

export default StreamerRegulars
