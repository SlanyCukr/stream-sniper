'use client'
import {
    Card, Row, Col,
} from 'react-bootstrap'
import ChatterSmallInfo from '../ChatterSmallInfo'

/** Ranked leaderboard column. */
const RankColumn = ({
    headingId, label, chatters, noun,
}) => (
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
                        key={chatter[0]}
                        rank={index + 1}
                        nick={chatter[1]}
                        count={chatter[2]}
                        noun={noun}
                    />
                ))}
            </ul>
        ) : (
            <p className="text-muted small mb-0">No data recorded.</p>
        )}
    </section>
)

/**
 * Stream Statistics Card Component
 */
const StreamStatsCard = ({
    mostActiveChatters, mostTaggedChatters, renderOtherCreators,
}) => (
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
            {renderOtherCreators}
        </Card.Body>
    </Card>
)

export default StreamStatsCard
