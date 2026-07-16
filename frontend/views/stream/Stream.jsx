'use client'
import {
    Row, Col,
} from 'react-bootstrap'
import { useStreamDetails } from '@/hooks/stream/list/useStreamsQuery'
import { useStreamTimeline } from '@/hooks/stream/timeline/useStreamTimelineQuery'
import { useStreamReplayController } from '@/hooks/stream/replay/useStreamReplayController'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import StreamInfoCard from '@/components/stream/StreamInfoCard'
import StreamDownloadMenu from '@/components/stream/StreamDownloadMenu'
import StreamTimeline from '@/components/stream/timeline/StreamTimeline'
import StreamMetrics from '@/components/stream/report/StreamMetrics'
import StreamReportCard from '@/components/stream/report/StreamReportCard'
import StreamStatsCard from '@/components/stream/report/StreamStatsCard'
import MentionsPanel from '@/components/stream/insights/MentionsPanel'
import EmotesPanel from '@/components/stream/insights/EmotesPanel'
import PhrasesPanel from '@/components/stream/insights/PhrasesPanel'
import StreamReplayCard from '@/components/stream/replay/StreamReplayCard'

const EMPTY_LIST = []
const EMPTY_STREAM_INFO = {}

/** @param {{streamId: number}} props */
const Stream = ({ streamId }) => {
    const {
        data: streamDetails,
        isLoading: isStreamLoading,
        error: streamError,
        refetch: refetchStreamData,
    } = useStreamDetails(streamId)

    const {
        data: timeline,
        error: timelineError,
        refetch: refetchTimeline,
    } = useStreamTimeline(streamId)

    const replay = useStreamReplayController(streamId)

    const streamInfoData = streamDetails?.info || EMPTY_STREAM_INFO

    const mostActiveChatters = streamDetails?.mostActiveChatters || EMPTY_LIST
    const mostTaggedChatters = streamDetails?.mostTaggedChatters || EMPTY_LIST
    const otherCreatorsThatWrote = streamDetails?.otherCreators || EMPTY_LIST
    const chattersInStream = streamDetails?.chatterOptions || EMPTY_LIST

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

    if(isStreamLoading){
        return (
            <LoadingSpinner
                size="lg"
                text="Loading stream data..."
                card
            />
        )
    }

    if(!streamDetails){
        return (
            <ErrorAlert
                error={new Error('The stream response did not contain stream data.')}
                title="Stream unavailable"
            />
        )
    }

    return (
        <>
            <StreamInfoCard
                streamInfoData={streamInfoData}
                downloadMenu={(
                    <StreamDownloadMenu
                        streamId={streamId}
                        title={streamInfoData.title}
                    />
                )}
            />

            <StreamReportCard streamId={streamId} />

            <StreamMetrics metrics={timeline?.metrics ?? null} />

            {timelineError ? (
                <ErrorAlert
                    error={timelineError}
                    title="Timeline unavailable"
                    onRetry={refetchTimeline} />
            ) : (
                <StreamTimeline
                    timeline={timeline}
                    onJump={replay.navigation.onJump} />
            )}

            {replay.navigation.jumpFailure && (
                <ErrorAlert
                    error={replay.navigation.jumpFailure.error}
                    title="Failed to load replay target" />
            )}

            <StreamStatsCard
                mostActiveChatters={mostActiveChatters}
                mostTaggedChatters={mostTaggedChatters}
                otherCreators={otherCreatorsThatWrote}
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
                replay={replay}
            />
        </>
    )
}

export default Stream
