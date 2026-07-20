'use client'

import { useCopyToClipboard } from '@/hooks/useCopyToClipboard'
import Link from 'next/link'
import {
    Card, Col, Row, Table,
} from 'react-bootstrap'
import {
    useChatterPassport,
    formatSharePct,
    shareBarWidth,
    type ChatterPassport as ChatterPassportModel,
} from '@/hooks/chatter/useChatterPassportQuery'
import CardLinkButton from '@/components/common/CardLinkButton'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import StatusChip from '@/components/common/StatusChip'
import ArchetypeBadges from '@/components/chatter/ArchetypeBadges'
import { formatCompactNumber } from '@/utils/numberUtils'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import { normalizeApiError } from '@/utils/errorUtils'

const CopyLinkButton = () => {
    const { copied, copy } = useCopyToClipboard()

    return (
        <button
            type="button"
            className="btn btn-outline-primary btn-sm"
            onClick={() => void copy(window.location.href)}
            aria-live="polite"
        >
            <i className={`bi ${copied ? 'bi-check2' : 'bi-link-45deg'} me-2`} aria-hidden="true" />
            {copied ? 'Link copied' : 'Copy link'}
        </button>
    )
}

const PassportBody = ({ passport }: { passport: ChatterPassportModel }) => {
    const {
        totals, debut, homeChannel, loyalty, milestones, companions,
    } = passport
    const mostActive = milestones.mostActiveStream

    const statTiles: Array<[string, string]> = [
        ['Messages', formatCompactNumber(totals.messages)],
        ['Streams attended', totals.streamsAttended.toLocaleString()],
        ['Channels visited', totals.creatorsVisited.toLocaleString()],
    ]

    return (
        <>
            <div className="stat-grid" role="list" aria-label="Chatter lifetime totals">
                {statTiles.map(([label, value]) => (
                    <div className="stat-tile" role="listitem" key={label}>
                        <div className="stat-label">{label}</div>
                        <div className="stat-value">{value}</div>
                    </div>
                ))}
            </div>

            <Row className="g-3 mb-4">
                <Col xs={12} md={4}>
                    <Card className="card-hud h-100">
                        <Card.Body>
                            <div className="section-label">Scene debut</div>
                            {debut ? (
                                <>
                                    <p className="fw-semibold mb-1">
                                        <Link href={`/stream/${debut.streamId}`}>{debut.streamTitle}</Link>
                                    </p>
                                    <p className="text-muted mb-0">
                                        {debut.creatorDisplayName}
                                        {' · '}
                                        <span className="mono small">{formatStreamTimestamp(debut.time)}</span>
                                    </p>
                                </>
                            ) : (
                                <p className="text-muted mb-0">First appearance unknown.</p>
                            )}
                        </Card.Body>
                    </Card>
                </Col>

                <Col xs={12} md={4}>
                    <Card className="card-hud h-100">
                        <Card.Body>
                            <div className="section-label">Home channel</div>
                            {homeChannel ? (
                                <>
                                    <p className="fw-semibold mb-1">{homeChannel.creatorDisplayName}</p>
                                    <p className="text-muted mb-0">
                                        {formatSharePct(homeChannel.share)} of all messages
                                        {' · '}
                                        <span className="mono">{homeChannel.messages.toLocaleString()}</span> msgs
                                    </p>
                                </>
                            ) : (
                                <p className="text-muted mb-0">No dominant channel yet.</p>
                            )}
                        </Card.Body>
                    </Card>
                </Col>

                <Col xs={12} md={4}>
                    <Card className="card-hud h-100">
                        <Card.Body>
                            <div className="section-label">Most active stream</div>
                            {mostActive ? (
                                <>
                                    <p className="fw-semibold mb-1">
                                        <Link href={`/stream/${mostActive.streamId}`}>{mostActive.title}</Link>
                                    </p>
                                    <p className="text-muted mb-0">
                                        {mostActive.creatorDisplayName}
                                        {' · '}
                                        <span className="mono">{mostActive.messages.toLocaleString()}</span> msgs
                                    </p>
                                </>
                            ) : (
                                <p className="text-muted mb-0">No standout stream yet.</p>
                            )}
                        </Card.Body>
                    </Card>
                </Col>
            </Row>

            <section>
                <div className="section-label">Channel loyalty</div>
                {loyalty.length ? (
                    <Table hover responsive>
                        <thead>
                            <tr>
                                <th scope="col">Channel</th>
                                <th scope="col" className="text-end">Messages</th>
                                <th scope="col" className="text-end">Streams</th>
                                <th scope="col">Share</th>
                            </tr>
                        </thead>
                        <tbody>
                            {loyalty.map(row => (
                                <tr key={row.creatorId}>
                                    <td>{row.creatorDisplayName}</td>
                                    <td className="mono text-end">{row.messages.toLocaleString()}</td>
                                    <td className="mono text-end">{row.streamsAttended.toLocaleString()}</td>
                                    <td style={{ minWidth: '120px' }}>
                                        <span className="mono small">{formatSharePct(row.share)}</span>
                                        <span className="data-bar" aria-hidden="true">
                                            <span
                                                className="data-bar-fill"
                                                style={{ width: `${shareBarWidth(row.share)}%` }}
                                            />
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                ) : (
                    <EmptyState title="No channel loyalty yet">
                        This chatter has not built up a per-channel history.
                    </EmptyState>
                )}
            </section>

            {companions.length ? (
                <section className="mt-4">
                    <div className="section-label">Chat companions</div>
                    <Card className="card-hud">
                        <Card.Body>
                            <Table hover responsive className="mb-0">
                                <thead>
                                    <tr>
                                        <th scope="col">Chatter</th>
                                        <th scope="col" className="text-end">Shared streams</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {companions.map(companion => (
                                        <tr key={companion.chatterId}>
                                            <td>
                                                <Link href={`/chatter/${companion.chatterId}`}>
                                                    {companion.nick}
                                                </Link>
                                            </td>
                                            <td className="mono text-end">
                                                {companion.sharedStreams.toLocaleString()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                        </Card.Body>
                    </Card>
                </section>
            ) : null}
        </>
    )
}

const ChatterPassport = ({ chatterId }: { chatterId: number }) => {
    const query = useChatterPassport(chatterId)
    const passport = query.data
    const chatter = passport?.chatter
    const totals = passport?.totals
    const notFound = query.error ? normalizeApiError(query.error).status === 404 : false

    const firstSeen = totals?.firstSeen ? formatStreamTimestamp(totals.firstSeen) : 'unknown'
    const lastSeen = totals?.lastSeen ? formatStreamTimestamp(totals.lastSeen) : 'unknown'

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">chatter passport</p>
                    <h1 className="page-title d-flex align-items-center gap-2">
                        {chatter?.nick ?? 'Chatter passport'}
                        {chatter?.isBot === true ? (
                            <span
                                title={chatter.botReason ?? undefined}
                                aria-label={
                                    chatter.botReason
                                        ? `Flagged as a bot: ${chatter.botReason}`
                                        : 'Flagged as a bot'
                                }
                            >
                                <StatusChip variant="warn">BOT</StatusChip>
                            </span>
                        ) : null}
                        {passport ? <ArchetypeBadges archetypes={passport.archetypes} /> : null}
                    </h1>
                    {passport ? (
                        <p className="page-sub mono small">
                            first seen {firstSeen} · last seen {lastSeen}
                        </p>
                    ) : null}
                </div>
                <div className="page-actions">
                    <CardLinkButton
                        entity="chatter"
                        id={chatterId}
                    />
                    <CopyLinkButton />
                </div>
            </div>

            {notFound ? (
                <EmptyState title="Chatter not found">
                    We couldn&apos;t find a chatter with this ID. It may have been removed, or the
                    link is out of date.
                </EmptyState>
            ) : (
                <QueryState
                    query={query}
                    errorTitle="Failed to load chatter passport"
                    loadingText="Assembling chatter passport..."
                    showErrorDetails={false}
                >
                    {(data: ChatterPassportModel) => <PassportBody passport={data} />}
                </QueryState>
            )}
        </>
    )
}

export default ChatterPassport
