'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    Card, Table,
} from 'react-bootstrap'
import Link from 'next/link'
import { useMessages } from '@/hooks/useApiQuery'
import PaginationComponent from '@/components/streams/PaginationComponent'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import { PAGINATION } from '@/constants'

/**
 * Messages tab of the chatter explorer: every individual message a chatter wrote
 * across captured streams, paginated. Owns its own pagination + query.
 *
 * Pagination resets naturally because the explorer remounts this panel (via a
 * `key` on the chatter id) whenever the selected chatter changes.
 *
 * @param {object} props
 * @param {{value: number, label: string}|null} props.chatter selected chatter option
 */
const ChatterMessagesPanel = ({ chatter }) => {
    const [
        offset,
        setOffset,
    ] = useState(PAGINATION.DEFAULT_OFFSET)

    const chatterId = chatter?.value || null

    const {
        data: messagesData,
        isLoading: messagesLoading,
        error: messagesError,
        refetch: refetchMessages,
    } = useMessages(chatterId, offset)

    const messages = useMemo(() => messagesData?.messages || [
    ], [
        messagesData?.messages,
    ])

    const total = messagesData?.total || 0
    const pagesCount = Math.ceil(total / PAGINATION.MESSAGES_PER_PAGE)

    /**
     * Updates offset
     * @param {Number} offsetParam
     */
    const updateOffset = useCallback(offsetParam => {
        setOffset(offsetParam)
    }, [
    ])

    const isLoading = Boolean(chatterId) && messagesLoading

    return (
        <>
            {chatter && total > 0 && !isLoading && (
                <div className="d-flex justify-content-end mb-2">
                    <span className="toolbar-readout">
                        <strong>{total.toLocaleString()}</strong> messages · target <strong>{chatter.label}</strong>
                    </span>
                </div>
            )}

            <Card>
                <Card.Body className={!chatter || (chatterId && messages.length === 0 && !isLoading) ? 'p-0' : ''}>
                    {!chatter && (
                        <div className="empty-state">
                            <div
                                className="empty-scope"
                                aria-hidden="true" />
                            <p className="empty-title">Awaiting target</p>
                            <p className="empty-hint">
                                Search for a chatter nickname to read everything they have written across captured streams.
                            </p>
                        </div>
                    )}

                    {isLoading && (
                        <LoadingSpinner
                            size="lg"
                            text="Loading chatter messages..."
                        />
                    )}

                    {messagesError && !isLoading && (
                        <ErrorAlert
                            error={messagesError}
                            title="Failed to load chatter messages"
                            onRetry={refetchMessages}
                            showDetails={process.env.NODE_ENV === 'development'}
                        />
                    )}

                    {chatterId && !isLoading && !messagesError && (
                        <div
                            role="region"
                            aria-label="Chatter messages results"
                            aria-live="polite"
                        >
                            {messages.length === 0
                                ? (
                                    <div className="empty-state">
                                        <div
                                            className="empty-scope"
                                            aria-hidden="true" />
                                        <p className="empty-title">No messages</p>
                                        <p className="empty-hint">This chatter has no recorded messages.</p>
                                    </div>
                                )
                                : (
                                    <>
                                        <div className="visually-hidden">
                                            {`Showing ${messages.length} of ${total} messages on page ${offset + 1} of ${pagesCount}`}
                                        </div>
                                        <Table
                                            hover
                                            responsive
                                        >
                                            <thead>
                                                <tr>
                                                    <th scope="col">Time</th>
                                                    <th scope="col">Streamer</th>
                                                    <th scope="col">Stream</th>
                                                    <th scope="col">Message</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {messages.map((row, rowIndex) => (
                                                    <tr key={`${offset}-${rowIndex}`}>
                                                        <td
                                                            className="mono small text-nowrap">
                                                            {formatStreamTimestamp(row[4])}
                                                        </td>
                                                        <td>{row[2]}</td>
                                                        <td>
                                                            <Link href={`/stream/${row[0]}`}>
                                                                {row[1]}
                                                            </Link>
                                                        </td>
                                                        <td>{row[3]}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </Table>
                                        <PaginationComponent
                                            pagesCount={pagesCount}
                                            offset={offset}
                                            updateOffset={updateOffset}
                                        />
                                    </>
                                )}
                        </div>
                    )}
                </Card.Body>
            </Card>
        </>
    )
}

export default ChatterMessagesPanel
