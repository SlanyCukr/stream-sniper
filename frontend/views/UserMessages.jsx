'use client'
import {
    useState, useCallback, useMemo,
} from 'react'
import {
    Card, Table,
} from 'react-bootstrap'
import Link from 'next/link'
import { useMessages } from '@/hooks/useApiQuery'
import { retrieveChatterSearch } from '@/lib/api'
import AsyncSearchSelect from '@/components/AsyncSearchSelect'
import PaginationComponent from '@/components/streams/PaginationComponent'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import { PAGINATION } from '@/constants'

const UserMessages = () => {
    const [
        selectedChatter,
        setSelectedChatter,
    ] = useState(null)
    const [
        offset,
        setOffset,
    ] = useState(PAGINATION.DEFAULT_OFFSET)

    const chatterId = selectedChatter?.value || null

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
     * Selects a chatter and resets pagination back to the first page.
     * @param {{value: number, label: string}|null} option
     */
    const handleChatterChange = useCallback(option => {
        setSelectedChatter(option)
        setOffset(PAGINATION.DEFAULT_OFFSET)
    }, [
    ])

    /**
     * Updates offset
     * @param {Number} offsetParam
     */
    const updateOffset = useCallback(offsetParam => {
        setOffset(offsetParam)
    }, [
    ])

    /**
     * Prefix-search chatter nicks for the autocomplete dropdown.
     * The backend returns [[id, nick], ...]; map to react-select options.
     * @param {string} query
     * @returns {Promise<Array<{value: number, label: string}>>}
     */
    const loadChatterOptions = useCallback(async query => {
        const trimmed = query.trim()
        if (trimmed.length < 2) {
            return []
        }
        try {
            const { data } = await retrieveChatterSearch(trimmed)
            return (data || []).map(([
                id,
                nick,
            ]) => ({
                value: id,
                label: nick,
            }))
        } catch {
            return []
        }
    }, [
    ])

    const noOptionsMessage = useCallback(({ inputValue }) => (
        inputValue && inputValue.trim().length >= 2
            ? `No chatters matching "${inputValue}"`
            : 'Type at least 2 characters to search'
    ), [
    ])

    const isLoading = Boolean(chatterId) && messagesLoading

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 id="chatter-messages-heading" className="page-title">Chatter messages</h1>
                    <p className="page-sub">Cross-stream message analysis</p>
                </div>
            </div>

            <div
                className="toolbar"
                role="search"
            >
                <span
                    className="toolbar-label"
                    aria-hidden="true">
                    Target
                </span>
                <div className="toolbar-field">
                    <label
                        htmlFor="chatter-messages-nick-input"
                        className="visually-hidden"
                    >
                        Chatter nickname
                    </label>
                    <AsyncSearchSelect
                        instanceId="chatter-messages-nick-select"
                        inputId="chatter-messages-nick-input"
                        loadOptions={loadChatterOptions}
                        value={selectedChatter}
                        onChange={handleChatterChange}
                        noOptionsMessage={noOptionsMessage}
                        placeholder="Search for a chatter..."
                        isClearable
                        aria-label="Chatter nickname"
                    />
                </div>
                {selectedChatter && total > 0 && !isLoading && (
                    <span className="toolbar-readout">
                        <strong>{total.toLocaleString()}</strong> messages · target <strong>{selectedChatter.label}</strong>
                    </span>
                )}
            </div>

            <Card>
                <Card.Body className={!selectedChatter || (chatterId && messages.length === 0 && !isLoading) ? 'p-0' : ''}>
                    {!selectedChatter && (
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
                            aria-labelledby="chatter-messages-heading"
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

export default UserMessages
