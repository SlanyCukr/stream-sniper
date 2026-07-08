'use client'
import { useMemo } from 'react'
import {
    Card, Row, Col,
} from 'react-bootstrap'
import { findThumbnailSrc } from '@/utils/utils'
import ThumbImage from './ThumbImage'

/**
 * Stream hero: thumbnail + identity + key numbers.
 */
const StreamInfoCard = ({
    streamInfoData, twitchLink, formattedStartTime, formattedEndTime, timeAgo, duration,
}) => {
    const {
        title, displayName, messageCount, thumbnailUrl,
    } = streamInfoData

    const heroThumb = useMemo(() => findThumbnailSrc(thumbnailUrl, 640, 360), [
        thumbnailUrl,
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">{displayName}</h1>
                    <p className="page-sub">Stream intel report</p>
                </div>
                <div className="page-actions">
                    <a
                        href={twitchLink}
                        target="_blank"
                        rel="noreferrer"
                        className="btn btn-outline-primary btn-sm"
                        aria-label={`Visit ${displayName}'s Twitch channel (opens in new tab)`}
                    >
                        <i
                            className="bi bi-twitch me-2"
                            aria-hidden="true"></i>
                        Twitch channel
                    </a>
                </div>
            </div>

            <Card className="card-hud">
                <Card.Body>
                    <Row className="g-4 align-items-center">
                        <Col
                            md={4}
                            lg={3}>
                            <div
                                className="thumb-wrap rounded overflow-hidden border"
                                style={{ aspectRatio: '16 / 9' }}>
                                <ThumbImage
                                    src={heroThumb}
                                    alt={`Stream thumbnail for ${displayName}`}
                                />
                            </div>
                        </Col>
                        <Col
                            md={8}
                            lg={9}>
                            <h2 className="fs-5 mb-3">{title}</h2>
                            <dl className="spec-list">
                                <dt>Messages</dt>
                                <dd className="mono">{messageCount?.toLocaleString()}</dd>
                                <dt>Duration</dt>
                                <dd className="mono">{duration}</dd>
                                <dt>Aired</dt>
                                <dd>{timeAgo}</dd>
                                <dt>Start</dt>
                                <dd className="mono">{formattedStartTime}</dd>
                                <dt>End</dt>
                                <dd className="mono">{formattedEndTime}</dd>
                            </dl>
                        </Col>
                    </Row>
                </Card.Body>
            </Card>
        </>
    )
}

export default StreamInfoCard
