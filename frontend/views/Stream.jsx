'use client'
import {
    useState,
    useCallback,
    useMemo,
} from 'react'
import {
    useStreamData,
    useChatterStreamMessages,
} from '@/hooks/useApiQuery'
import LazyTwitchChatLookalike from '@/components/LazyTwitchChatLookalike'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'
import StreamInfoCard from '@/components/streams/StreamInfoCard'
import StreamStatsCard from '@/components/streams/StreamStatsCard'
import ChatSearchCard from '@/components/streams/ChatSearchCard'
import {
    formatStreamTimestamp, formatTimeAgo, formatDurationBetween,
} from '@/utils/dateUtils'


const Stream = ({ streamId }) => {
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

            <StreamStatsCard
                mostActiveChatters={mostActiveChatters}
                mostTaggedChatters={mostTaggedChatters}
                renderOtherCreators={renderOtherCreators}
            />

            <ChatSearchCard
                chattersInStream={chattersInStream}
                selectedChatterOption={selectedChatterOption}
                handleChatterSelection={handleChatterSelection}
                isMessagesLoading={isMessagesLoading}
                messagesError={messagesError}
                renderTwitchChat={renderTwitchChat}
            />
        </>
    )
}

export default Stream
