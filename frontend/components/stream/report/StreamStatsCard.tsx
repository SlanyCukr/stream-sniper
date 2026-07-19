'use client'
import {
    Card, Row, Col,
} from 'react-bootstrap'
import ChatterSmallInfo from './ChatterSmallInfo'
import StatusChip from '@/components/common/StatusChip'
import type { RankedChatter, StreamCreator } from '@/hooks/stream/list/useStreamsQuery'

interface RankColumnProps {
    headingId: string
    label: string
    chatters: RankedChatter[]
    noun: string
}

const RankColumn = ({
    headingId, label, chatters, noun,
}: RankColumnProps) => (
    <section aria-labelledby={headingId}>
        <h3
            id={headingId}
            className="section-label mb-3">
            {label}
        </h3>
        {chatters?.length ? (
            <ul
                className="rank-list"
                role="list"
                aria-label={label}>
                {chatters.map((chatter, index) => (
                    <ChatterSmallInfo
                        key={chatter.chatterId}
                        rank={index + 1}
                        nick={chatter.nick}
                        count={chatter.count}
                        noun={noun}
                    />
                ))}
            </ul>
        ) : (
            <p className="text-muted small mb-0">No data recorded.</p>
        )}
    </section>
)

const OtherCreatorsInChat = ({ creators }: { creators: StreamCreator[] }) => (
    creators.length ? (
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
                {creators.map(creator => (
                    <StatusChip
                        key={creator.creatorId}
                        role="listitem">
                        {creator.nick}
                    </StatusChip>
                ))}
            </div>
        </section>
    ) : null
)

interface StreamStatsCardProps {
    mostActiveChatters: RankedChatter[]
    mostTaggedChatters: RankedChatter[]
    otherCreators: StreamCreator[]
}

const StreamStatsCard = ({
    mostActiveChatters, mostTaggedChatters, otherCreators,
}: StreamStatsCardProps) => (
    <Card>
        <Card.Body>
            <Row className="g-4">
                <Col md={6}>
                    <RankColumn
                        headingId="most-active-heading"
                        label="Most active chatters"
                        chatters={mostActiveChatters}
                        noun="messages"
                    />
                </Col>
                <Col md={6}>
                    <RankColumn
                        headingId="most-tagged-heading"
                        label="Most tagged chatters"
                        chatters={mostTaggedChatters}
                        noun="tags"
                    />
                </Col>
            </Row>
            <OtherCreatorsInChat creators={otherCreators} />
        </Card.Body>
    </Card>
)

export default StreamStatsCard
