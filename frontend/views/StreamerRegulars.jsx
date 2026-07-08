'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import Select from 'react-select'
import {
    Card, Container, Row, Col, Table,
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
            {creatorsError && (
                <ErrorAlert
                    error={creatorsError}
                    title="Failed to load creators"
                    onRetry={refetchCreators}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}

            <Card className="mb-4">
                <Card.Header>
                    <h2 id="regulars-filter-heading" className="page-title fs-6 mb-0">Select creator</h2>
                </Card.Header>
                <Card.Body>
                    <Container>
                        <Row>
                            <Col>
                                <label
                                    htmlFor="regulars-creator-select"
                                    className="visually-hidden"
                                >
                                    Select a creator
                                </label>
                                <Select
                                    instanceId="regulars-creator-select"
                                    inputId="regulars-creator-select"
                                    options={creators}
                                    value={selectedCreator}
                                    onChange={handleCreatorChange}
                                    placeholder="Select creator..."
                                    isClearable
                                    aria-label="Select a creator to view their regulars"
                                />
                            </Col>
                        </Row>
                    </Container>
                </Card.Body>
            </Card>

            <Card>
                <Card.Header>
                    <h1 id="regulars-heading" className="page-title mb-0">Streamer regulars</h1>
                </Card.Header>
                <Card.Body>
                    {!selectedCreatorId && (
                        <p className="mb-0">Select a creator to see their most active chatters across all streams.</p>
                    )}

                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Loading regulars..."
                            card
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
                                ? <p className="mb-0">No chatters found for this creator.</p>
                                : (
                                    <Table
                                        striped
                                        hover
                                        responsive
                                    >
                                        <thead>
                                            <tr>
                                                <th scope="col">#</th>
                                                <th scope="col">Chatter</th>
                                                <th scope="col">Messages</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {topChatters.map((chatter, index) => (
                                                <tr key={chatter[0]}>
                                                    <td>{index + 1}</td>
                                                    <td>{chatter[1]}</td>
                                                    <td>{chatter[2]?.toLocaleString()}</td>
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
