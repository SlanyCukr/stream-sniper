import Link from 'next/link'
import { Card } from 'react-bootstrap'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import { formatCompactNumber } from '@/utils/numberUtils'

const SignatureCard = ({
    title, query, loadingText, className, children,
}) => (
    <Card className={className}>
        <Card.Body>
            <div className="section-label">{title}</div>
            {query.isLoading ? <LoadingSpinner text={loadingText} /> : null}
            {query.error ? <ErrorAlert error={query.error} title={`Failed to load ${title.toLowerCase()}`} onRetry={query.refetch} /> : null}
            {!query.isLoading && !query.error ? <ol className="rank-list">{children}</ol> : null}
        </Card.Body>
    </Card>
)

const CreatorSignatureCards = ({
    emotesQuery, neighborsQuery, copypastasQuery,
}) => (
    <div className="dossier-grid">
        <SignatureCard title="Signature emotes" query={emotesQuery} loadingText="Loading emotes...">
            {(emotesQuery.data?.emotes || []).map((emote, index) => (
                <li key={`${emote.source}:${emote.name}`}>
                    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                    <span className="nick">{emote.name}</span>
                    <span className="count">{formatCompactNumber(emote.usageCount)}</span>
                </li>
            ))}
        </SignatureCard>
        <SignatureCard title="Audience also watches" query={neighborsQuery} loadingText="Loading neighbors...">
            {(neighborsQuery.data?.neighbors || []).map((neighbor, index) => (
                <li key={neighbor.creatorId}>
                    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                    <Link className="nick" href={`/creator/${neighbor.creatorId}`}>
                        {neighbor.displayName || neighbor.nick}
                    </Link>
                    <span className="count">{neighbor.sharedRegulars} shared</span>
                </li>
            ))}
        </SignatureCard>
        <SignatureCard
            title="Signature copypastas"
            query={copypastasQuery}
            loadingText="Loading copypastas..."
            className="dossier-copypastas"
        >
            {(copypastasQuery.data?.items || []).map((item, index) => (
                <li key={item.messageTextId}>
                    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                    <Link className="nick text-truncate" href={`/copypasta/${item.messageTextId}`}>
                        {item.text}
                    </Link>
                    <span className="count">{item.usageCount}×</span>
                </li>
            ))}
        </SignatureCard>
    </div>
)

export default CreatorSignatureCards
