import {
    Card,
} from 'react-bootstrap'

/**
 * Stream Information Card Component
 */
const StreamInfoCard = ({
    streamInfoData, twitchLink, formattedStartTime, formattedEndTime, timeAgo, duration,
}) => {
    const {
        title, displayName, messageCount,
    } = streamInfoData

    return (
        <Card>
            <Card.Body>
                <Card.Title as="h1">{title}</Card.Title>
                <Card.Subtitle
                    className="mb-2 text-muted"
                    as="h2">
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
    )
}

export default StreamInfoCard
