'use client'
import {
    useState,
    useRef,
    useCallback,
    useMemo,
} from 'react'
import {
    Row, Col,
} from 'react-bootstrap'
import {
    useStreamData,
    useStreamMessages,
    useStreamTimeline,
} from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import StreamInfoCard from '@/components/streams/StreamInfoCard'
import StreamTimeline from '@/components/streams/StreamTimeline'
import StreamMetrics from '@/components/streams/StreamMetrics'
import StreamStatsCard from '@/components/streams/StreamStatsCard'
import MentionsPanel from '@/components/streams/MentionsPanel'
import EmotesPanel from '@/components/streams/EmotesPanel'
import PhrasesPanel from '@/components/streams/PhrasesPanel'
import StreamReplayCard from '@/components/streams/StreamReplayCard'
import {
    formatStreamTimestamp, formatTimeAgo, formatDurationBetween,
} from '@/utils/dateUtils'


const Stream = ({ streamId }) => {
    // Replay filters (server-side); the child StreamReplayCard drives these.
    const [
        chatterId,
        setChatterId,
    ] = useState(undefined)
    const [
        textQuery,
        setTextQuery,
    ] = useState(undefined)
    const [
        subOnly,
        setSubOnly,
    ] = useState(false)

    // Lifted jump target. A timeline moment (T12) will set this via handleJump;
    // StreamChatReplay reacts to the object identity change (nonce) to scroll+flash.
    const [
        jumpToTs,
        setJumpToTs,
    ] = useState(null)

    // Use TanStack Query hooks for data fetching
    const {
        data: streamInfo,
        isLoading: isStreamLoading,
        error: streamError,
        refetch: refetchStreamData,
    } = useStreamData(streamId)

    // The full chronological replay lives HERE (not in StreamReplayCard) so the
    // timeline jump handler below can drive fetchNextPage until the target row
    // is loaded, then scroll to it.
    const {
        data: messagesData,
        error: messagesError,
        isLoading: isMessagesLoading,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
    } = useStreamMessages(streamId, {
        chatterId,
        q: textQuery,
        subOnly,
    })

    // Timeline (buckets + moments + metrics) powers the activity chart and the
    // metric tiles. Absent rollups -> empty buckets + null metrics (handled by
    // the child components, so raw replay still works).
    const { data: timeline } = useStreamTimeline(streamId)

    const replayMessages = useMemo(
        () => messagesData?.pages.flatMap(page => page.messages) ?? [],
        [
            messagesData,
        ],
    )

    const handleLoadMore = useCallback(() => {
        if (hasNextPage && !isFetchingNextPage) {
            fetchNextPage()
        }
    }, [
        hasNextPage,
        isFetchingNextPage,
        fetchNextPage,
    ])

    // Guards against overlapping jump loops (double-clicked moment markers).
    const jumpingRef = useRef(false)

    /**
     * Jump the replay to a timestamp: page forward until a row at/after the
     * target is loaded (or there are no more pages), then flag the scroll.
     * Wired to T12's StreamTimeline moment markers.
     * @param {string} targetTs - ISO timestamp of the moment to jump to
     */
    const handleJump = useCallback(async targetTs => {
        if (!targetTs || jumpingRef.current) {
            return
        }
        const reached = pages => pages.some(
            page => page.messages.some(message => message.ts >= targetTs),
        )
        jumpingRef.current = true
        try {
            let current = messagesData
            let canFetch = hasNextPage
            let guard = 0
            while (current && !reached(current.pages) && canFetch && guard < 1000) {
                const result = await fetchNextPage()
                current = result.data
                canFetch = result.hasNextPage
                guard += 1
            }
            setJumpToTs({
                ts: targetTs,
                nonce: Date.now(),
            })
        } finally {
            jumpingRef.current = false
        }
    }, [
        messagesData,
        hasNextPage,
        fetchNextPage,
    ])

    // Extract stream info with memoization to prevent re-extraction on every render
    const csi = streamInfo?.csi
    const streamInfoData = useMemo(() => {
        if (!csi) {
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
        ] = csi

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
        csi,
    ])

    const {
        start,
        end,
        nick,
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
            <section
                aria-labelledby="other-creators-heading"
                className="mt-4">
                <h3
                    id="other-creators-heading"
                    className="section-label mb-3">
                    Other creators in chat
                </h3>
                <div
                    className="d-flex flex-wrap gap-2"
                    role="list"
                    aria-label="Other creators who participated in this stream">
                    {otherCreatorsThatWrote?.map(creator => (
                        <span
                            key={creator[0]}
                            role="listitem"
                            className="status-chip">
                            {creator[1]}
                        </span>
                    ))}
                </div>
            </section>
        )
    }, [
        otherCreatorsThatWrote,
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

    return (
        <>
            <StreamInfoCard
                streamInfoData={streamInfoData}
                twitchLink={twitchLink}
                formattedStartTime={formattedStartTime}
                formattedEndTime={formattedEndTime}
                timeAgo={timeAgo}
                duration={duration}
            />

            <StreamTimeline
                timeline={timeline}
                onJump={handleJump}
            />

            <StreamMetrics metrics={timeline?.metrics} />

            <StreamStatsCard
                mostActiveChatters={mostActiveChatters}
                mostTaggedChatters={mostTaggedChatters}
                renderOtherCreators={renderOtherCreators}
            />

            <Row className="g-4">
                <Col lg={4}>
                    <MentionsPanel streamId={streamId} />
                </Col>
                <Col lg={4}>
                    <EmotesPanel streamId={streamId} />
                </Col>
                <Col lg={4}>
                    <PhrasesPanel streamId={streamId} />
                </Col>
            </Row>

            <StreamReplayCard
                chatterOptions={chattersInStream}
                onChatterChange={setChatterId}
                onQueryChange={setTextQuery}
                onSubOnlyChange={setSubOnly}
                messages={replayMessages}
                hasMore={Boolean(hasNextPage)}
                isFetchingMore={isFetchingNextPage}
                onLoadMore={handleLoadMore}
                isLoading={isMessagesLoading}
                error={messagesError}
                jumpToTs={jumpToTs}
            />
        </>
    )
}

export default Stream
