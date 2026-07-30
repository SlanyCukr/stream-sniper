'use client'
import {
    Row, Col,
} from 'react-bootstrap'
import { useStreamDetails } from '@/hooks/stream/list/useStreamsQuery'
import { useStreamTimeline } from '@/hooks/stream/timeline/useStreamTimelineQuery'
import { useStreamReplayController } from '@/hooks/stream/replay/useStreamReplayController'
import CardLinkButton from '@/components/common/CardLinkButton'
import QueryState from '@/components/common/QueryState'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import { uiError } from '@/utils/errorUtils'
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

interface StreamProps {
    streamId: number
}

const Stream = ({ streamId }: StreamProps) => {
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

    return (
        <QueryState
            query={{
                data: streamDetails, isLoading: isStreamLoading, error: streamError, refetch: refetchStreamData,
            }}
            errorTitle="Failed to load stream"
            loadingText="Loading stream data..."
            loadingCard
            emptyState={(
                <ErrorAlert
                    error={uiError("This stream couldn't be displayed. Refresh the page to try again.")}
                    title="Stream unavailable"
                />
            )}
        >
            {(details) => (
                <>
                    <StreamInfoCard
                        streamInfoData={details.info}
                        downloadMenu={(
                            <>
                                <CardLinkButton
                                    entity="stream"
                                    id={streamId}
                                />
                                <StreamDownloadMenu
                                    streamId={streamId}
                                    title={details.info.title}
                                />
                            </>
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
                        mostActiveChatters={details.mostActiveChatters}
                        mostTaggedChatters={details.mostTaggedChatters}
                        otherCreators={details.otherCreators}
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
                        chatterOptions={details.chatterOptions}
                        replay={replay}
                    />
                </>
            )}
        </QueryState>
    )
}

export default Stream
