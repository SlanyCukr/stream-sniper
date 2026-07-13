'use client'

import Link from 'next/link'
import { Card } from 'react-bootstrap'
import {
    useCreatorEmotes,
    useCreatorNeighbors,
    useCreatorSummary,
    useSceneCopypastas,
} from '@/hooks/useApiQuery'
import ErrorAlert from '@/components/ErrorAlert'
import LoadingSpinner from '@/components/LoadingSpinner'
import RegularsPanel from '@/components/creator/RegularsPanel'
import TrendsPanel from '@/components/creator/TrendsPanel'
import { formatTimeAgo } from '@/utils/dateUtils'

const compact = value => new Intl.NumberFormat('en', {
    notation: 'compact',
    maximumFractionDigits: 1,
}).format(value || 0)

const duration = seconds => {
    if (seconds == null) return '--'
    return `${Math.round(seconds / 3600).toLocaleString()}h`
}

const CreatorDossier = ({ creatorId }) => {
    const summaryQuery = useCreatorSummary(creatorId)
    const emotesQuery = useCreatorEmotes(creatorId, 8)
    const neighborsQuery = useCreatorNeighbors(creatorId, { metric: 'regulars', limit: 6 })
    const copypastasQuery = useSceneCopypastas({ creatorId, sort: 'usage', limit: 5 })

    if (!Number.isInteger(creatorId) || creatorId <= 0) {
        return <ErrorAlert title="Invalid creator" error={new Error('Creator ID must be a positive integer.')} />
    }
    if (summaryQuery.isLoading) return <LoadingSpinner size="lg" text="Building creator dossier..." />
    if (summaryQuery.error) {
        return <ErrorAlert title="Failed to load creator" error={summaryQuery.error} onRetry={summaryQuery.refetch} />
    }

    const creator = summaryQuery.data
    const stats = [
        ['Streams', creator.totalStreams.toLocaleString()],
        ['Chat messages', compact(creator.totalMessages)],
        ['Hours captured', duration(creator.durationSeconds)],
        ['Avg msgs/min', creator.messagesPerMinute == null ? '--' : creator.messagesPerMinute.toFixed(1)],
        ['Known audience', compact(creator.audienceSize)],
        ['Regulars', creator.regulars.toLocaleString()],
    ]

    return (
        <>
            <header className="page-header creator-dossier-header">
                <div className="creator-identity">
                    {creator.profileImageUrl ? (
                        <img className="creator-avatar" src={creator.profileImageUrl} alt="" />
                    ) : null}
                    <div>
                        <p className="page-sub">creator dossier · last seen {creator.lastStreamAt ? formatTimeAgo(creator.lastStreamAt) : 'never'}</p>
                        <h1 className="page-title">{creator.displayName || creator.nick}</h1>
                        <p className="mono text-muted">@{creator.nick}</p>
                    </div>
                </div>
                <div className="d-flex gap-2">
                    <Link className="btn btn-outline-primary btn-sm" href={`/movement?creator=${creatorId}`}>
                        Audience movement
                    </Link>
                    {creator.latestStream ? (
                        <Link className="btn btn-outline-primary btn-sm" href={`/stream/${creator.latestStream.streamId}`}>
                            Latest stream
                        </Link>
                    ) : null}
                </div>
            </header>

            <div className="stats-strip" role="list" aria-label="Creator lifetime statistics">
                {stats.map(([label, value]) => (
                    <div className="stat-tile" role="listitem" key={label}>
                        <div className="stat-label">{label}</div>
                        <div className="stat-value">{value}</div>
                    </div>
                ))}
            </div>

            <section className="dossier-section">
                <div className="section-label">Recent trajectory</div>
                <TrendsPanel creatorId={creatorId} />
            </section>

            <div className="dossier-grid">
                <Card>
                    <Card.Body>
                        <div className="section-label">Signature emotes</div>
                        {emotesQuery.isLoading && <LoadingSpinner text="Loading emotes..." />}
                        <ol className="rank-list">
                            {(emotesQuery.data?.emotes || []).map((emote, index) => (
                                <li key={`${emote.source}:${emote.name}`}>
                                    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                                    <span className="nick">{emote.name}</span>
                                    <span className="count">{compact(emote.usageCount)}</span>
                                </li>
                            ))}
                        </ol>
                    </Card.Body>
                </Card>

                <Card>
                    <Card.Body>
                        <div className="section-label">Audience also watches</div>
                        {neighborsQuery.isLoading && <LoadingSpinner text="Loading neighbors..." />}
                        <ol className="rank-list">
                            {(neighborsQuery.data?.neighbors || []).map((neighbor, index) => (
                                <li key={neighbor.creatorId}>
                                    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                                    <Link className="nick" href={`/creator/${neighbor.creatorId}`}>
                                        {neighbor.displayName || neighbor.nick}
                                    </Link>
                                    <span className="count">{neighbor.sharedRegulars} shared</span>
                                </li>
                            ))}
                        </ol>
                    </Card.Body>
                </Card>

                <Card className="dossier-copypastas">
                    <Card.Body>
                        <div className="section-label">Signature copypastas</div>
                        {copypastasQuery.isLoading && <LoadingSpinner text="Loading copypastas..." />}
                        <ol className="rank-list">
                            {(copypastasQuery.data?.items || []).map((item, index) => (
                                <li key={item.messageTextId}>
                                    <span className="rank">{String(index + 1).padStart(2, '0')}</span>
                                    <Link className="nick text-truncate" href={`/copypasta/${item.messageTextId}`}>
                                        {item.text}
                                    </Link>
                                    <span className="count">{item.usageCount}×</span>
                                </li>
                            ))}
                        </ol>
                    </Card.Body>
                </Card>
            </div>

            <section className="dossier-section">
                <div className="section-label">Core regulars</div>
                <RegularsPanel creatorId={creatorId} />
            </section>
        </>
    )
}

export default CreatorDossier
