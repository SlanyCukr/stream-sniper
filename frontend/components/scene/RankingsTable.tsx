'use client'

import Link from 'next/link'
import { Card, Table } from 'react-bootstrap'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'
import type { RankingsRow } from '@/hooks/scene/useSceneRankingsQueries'
import ArchetypeBadges from '@/components/chatter/ArchetypeBadges'

interface RankingsTableProps {
    rows: RankingsRow[]
    hasMore: boolean
    isFetchingMore: boolean
    onLoadMore: () => void
    /**
     * Shown as a single message row instead of the (empty) row list when
     * client-side archetype filters have hidden every loaded row. Load more
     * still renders below so more rows remain reachable.
     */
    filterEmptyMessage?: string
}

/**
 * Server-ranked chatter leaderboard. Rows arrive already ordered by rank, so
 * this table only renders (no client sort); the message bars are scaled to the
 * leading row so relative volume reads at a glance.
 */
const RankingsTable = ({
    rows, hasMore, isFetchingMore, onLoadMore, filterEmptyMessage,
}: RankingsTableProps) => {
    const topMessages = rows.reduce((max, row) => Math.max(max, row.totalMessages), 0)

    return (
        <>
            <Card>
                <Card.Body className="p-0">
                    <div role="region" aria-label="Scene power rankings">
                        <Table hover responsive className="mb-0">
                            <thead>
                                <tr>
                                    <th scope="col">#</th>
                                    <th scope="col">Chatter</th>
                                    <th scope="col" className="text-end">Messages</th>
                                    <th scope="col" className="text-end">Streams</th>
                                    <th scope="col" className="text-end">Channels</th>
                                    <th scope="col">Home channel</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows.length === 0 && filterEmptyMessage ? (
                                    <tr>
                                        <td colSpan={6} className="rankings-filter-empty text-center">
                                            {filterEmptyMessage}
                                        </td>
                                    </tr>
                                ) : rows.map(row => (
                                    <tr key={row.chatterId}>
                                        <td className="rank-num">{String(row.rank).padStart(2, '0')}</td>
                                        <td>
                                            <Link className="rankings-nick" href={`/chatter/${row.chatterId}`}>
                                                {row.nick}
                                            </Link>
                                            {row.archetypes.length > 0 ? (
                                                <div className="rankings-archetypes">
                                                    <ArchetypeBadges archetypes={row.archetypes} />
                                                </div>
                                            ) : null}
                                        </td>
                                        <td className="rankings-messages text-end">
                                            <span className="rankings-messages-value mono">
                                                {formatCompactNumber(row.totalMessages)}
                                            </span>
                                            <span className="data-bar" aria-hidden="true">
                                                <span
                                                    className="data-bar-fill"
                                                    style={{ width: `${magnitudeBarWidth(row.totalMessages, topMessages)}%` }}
                                                />
                                            </span>
                                        </td>
                                        <td className="mono text-end">{row.streamsAttended.toLocaleString()}</td>
                                        <td className="mono text-end">{row.creatorsVisited.toLocaleString()}</td>
                                        <td>
                                            {row.homeChannel ? (
                                                <span className="rankings-home">
                                                    <Link href={`/creator/${row.homeChannel.creatorId}`}>
                                                        {row.homeChannel.creatorDisplayName}
                                                    </Link>
                                                    <span className="rankings-home-share mono small">
                                                        {`${(row.homeChannel.share * 100).toFixed(1)}%`}
                                                    </span>
                                                </span>
                                            ) : (
                                                <span className="rankings-home-empty">—</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </Table>
                    </div>
                </Card.Body>
            </Card>
            {hasMore ? (
                <div className="rankings-load-more">
                    <button
                        type="button"
                        className="btn btn-outline-primary btn-sm"
                        onClick={onLoadMore}
                        disabled={isFetchingMore}
                    >
                        {isFetchingMore ? 'Loading…' : 'Load more'}
                    </button>
                </div>
            ) : null}
        </>
    )
}

export default RankingsTable
