import {
    useState,
    useCallback,
    useMemo,
} from 'react'
import { useParams } from 'react-router-dom'
import Select from 'react-select'
import {
    Card,
} from 'react-bootstrap'
import {
    useStreamData,
    useChatterStreamMessages,
} from '../../hooks/useApiQuery'
import ChatterSmallInfo from '../../components/ChatterSmallInfo'
import LazyTwitchChatLookalike from '../../components/LazyTwitchChatLookalike'
import LoadingSpinner from '../../components/LoadingSpinner'
import ErrorAlert from '../../components/ErrorAlert'
import {
    formatStreamTimestamp, formatTimeAgo, formatDurationBetween,
} from '../../utils/dateUtils'

const Stream = () => {
    const params = useParams()
    const streamId = params.id

    const [
        selectedChatterOption,
        setSelectedChatterOption,
    ] = useState({})

    // Use TanStack Query hooks for data fetching
    const {
        data: streamInfo,
        isLoading: isStreamLoading,
        error: streamError,
        refetch: refetchStreamData,
    } = useStreamData(streamId)

    const {
        data: selectedChatterMessages = [
        ],
        isLoading: isMessagesLoading,
        error: messagesError,
    } = useChatterStreamMessages(
        streamId,
        selectedChatterOption.value,
        {
            enabled: Boolean(selectedChatterOption.value), // Only fetch when chatter is selected
        },
    )

    /**
     * Handles chatter selection and sets up message fetching.
     * @param {Object} selectedOption   // option selected in Select component 
     */
    const handleChatterSelection = useCallback(selectedOption => {
        setSelectedChatterOption(selectedOption)
    }, [
    ])

    if(isStreamLoading || !streamInfo){
        return (
            <LoadingSpinner 
                size="lg"
                text="Loading stream data..."
                card
            />
        )
    }

    if(streamError){
        return (
            <ErrorAlert
                error={streamError}
                title="Failed to load stream"
                onRetry={refetchStreamData}
                showDetails={process.env.NODE_ENV === 'development'}
            />
        )
    }

    // Extract stream info with memoization to prevent re-extraction on every render
    const streamInfoData = useMemo(() => {
        if (!streamInfo?.csi) {
            return {}
        }

        const [
            title,
            start,
            end,
            thumbnailUrl,
            messageCount,
            nick,
            displayName,
            profileImageUrl,
            creatorId,
        ] = streamInfo.csi

        return {
            title,
            start,
            end,
            thumbnailUrl,
            messageCount,
            nick,
            displayName,
            profileImageUrl,
            creatorId,
        }
    }, [
        streamInfo?.csi,
    ])

    const {
        title,
        start,
        end,
        thumbnailUrl,
        messageCount,
        nick,
        displayName,
        profileImageUrl,
        creatorId,
    } = streamInfoData

    // Memoize expensive data transformations
    const mostActiveChatters = useMemo(() => streamInfo?.mac || [
    ], [
        streamInfo?.mac,
    ])
    const mostTaggedChatters = useMemo(() => streamInfo?.mtc || [
    ], [
        streamInfo?.mtc,
    ])
    const otherCreatorsThatWrote = useMemo(() => streamInfo?.octw || [
    ], [
        streamInfo?.octw,
    ])

    const chattersInStream = useMemo(() => streamInfo?.cis?.map(chatter => ({
        label: chatter[1],
        value: chatter[0],
    })) || [
    ], [
        streamInfo?.cis,
    ])

    const twitchLink = useMemo(() => `https://twitch.tv/${nick}`, [
        nick,
    ])

    // Memoize date calculations for performance
    const formattedStartTime = useMemo(() => formatStreamTimestamp(start), [
        start,
    ])
    const formattedEndTime = useMemo(() => formatStreamTimestamp(end), [
        end,
    ])
    const timeAgo = useMemo(() => formatTimeAgo(start), [
        start,
    ])
    const duration = useMemo(() => formatDurationBetween(start, end), [
        start,
        end,
    ])

    /**
     * Renders other creators with memoization.
     * @returns {JSX.Element}
     */
    const renderOtherCreators = useMemo(() => {
        if(otherCreatorsThatWrote?.length === 0){
            return null
        }

        return(
            <section aria-labelledby="other-creators-heading">
                <h3 id="other-creators-heading">Other creators that wrote</h3>
                <ul
                    role="list"
                    aria-label="Other creators who participated in this stream">
                    {otherCreatorsThatWrote?.map(creator => <li key={creator[0]}>{creator[1]}</li>)}
                </ul>
            </section>
        )
    }, [
        otherCreatorsThatWrote,
    ])

    /**
     * Renders Twitch chat lookalike component with memoization.
     * @returns {JSX.Element}
    */
    const renderTwitchChat = useMemo(() => {
        if(!selectedChatterOption.label){
            return null
        }

        return(
            <LazyTwitchChatLookalike
                nick={selectedChatterOption.label}
                messages={selectedChatterMessages}
            />
        )
    }, [
        selectedChatterOption.label,
        selectedChatterMessages,
    ])

    return(
        <>
            <Card>
                <Card.Body>
                    <Card.Title as="h1">{title}</Card.Title>
                    <Card.Subtitle
                        className="mb-2 text-muted"
                        as="h2"
                    >
                        {displayName}
                    </Card.Subtitle>
                    <dl>
                        <dt>Twitch link:</dt>
                        <dd>
                            <a
                                href={twitchLink}
                                target="_blank"
                                rel="noreferrer"
                                aria-label={`Visit ${displayName}'s Twitch channel (opens in new tab)`}
                            >
                                {twitchLink}
                            </a>
                        </dd>
                        <dt>Message count:</dt>
                        <dd><span className="fw-bold">{messageCount}</span></dd>
                        <dt>Start time:</dt>
                        <dd><span className="fw-bold">{formattedStartTime}</span></dd>
                        <dt>End time:</dt>
                        <dd><span className="fw-bold">{formattedEndTime}</span></dd>
                        <dt>Time ago:</dt>
                        <dd><span className="fw-bold">{timeAgo}</span></dd>
                        <dt>Duration:</dt>
                        <dd><span className="fw-bold">{duration}</span></dd>
                    </dl>
                </Card.Body>
            </Card>
            <Card>
                <Card.Body>
                    <section aria-labelledby="most-active-heading">
                        <h3 id="most-active-heading">Most active chatters</h3>
                        <ul
                            role="list"
                            aria-label="Most active chatters in this stream">
                            {mostActiveChatters?.map(chatter => (
                                <ChatterSmallInfo
                                    key={chatter[0]}
                                    id={chatter[0]}
                                    nick={chatter[1]}
                                    count={chatter[2]}
                                    noun="Count"
                                />
                            ))}
                        </ul>
                    </section>
                    <section aria-labelledby="most-tagged-heading">
                        <h3 id="most-tagged-heading">Most tagged chatters</h3>
                        <ul
                            role="list"
                            aria-label="Most tagged chatters in this stream">
                            {mostTaggedChatters?.map(chatter => (
                                <ChatterSmallInfo
                                    key={chatter[0]}
                                    id={chatter[0]}
                                    nick={chatter[1]}
                                    count={chatter[2]}
                                    noun="Tagged"
                                />
                            ))}
                        </ul>
                    </section>
                    {renderOtherCreators}
                </Card.Body>
            </Card>
            <Card>
                <Card.Body>
                    <Card.Title
                        as="h2"
                        id="chat-search-heading">Searching for messages in this stream</Card.Title>
                    <div
                        role="search"
                        aria-labelledby="chat-search-heading">
                        <label
                            htmlFor="chatter-select"
                            className="visually-hidden">
                            Select a chatter to view their messages
                        </label>
                        <Select
                            inputId="chatter-select"
                            options={chattersInStream}
                            value={selectedChatterOption}
                            onChange={handleChatterSelection}
                            placeholder="Select a chatter to view their messages..."
                            aria-label="Choose a chatter to view their messages in this stream"
                            aria-describedby="chatter-help"
                        />
                        <div
                            id="chatter-help"
                            className="visually-hidden">
                            Choose a chatter from the dropdown to see all their messages during this stream
                        </div>
                    </div>
                    {isMessagesLoading && (
                        <div
                            className="mt-2"
                            role="status"
                            aria-live="polite"
                            aria-label="Loading messages"
                        >
                            Loading messages...
                        </div>
                    )}
                    {messagesError && (
                        <div
                            className="mt-2 text-danger"
                            role="alert"
                            aria-live="assertive"
                        >
                            Error loading messages: {messagesError.response?.data?.message || messagesError.message}
                        </div>
                    )}
                    {renderTwitchChat}
                </Card.Body>
            </Card>
        </>
    )
}

export default Stream
