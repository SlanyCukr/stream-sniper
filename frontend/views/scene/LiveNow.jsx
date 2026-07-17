'use client'
import { useMemo } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { Card } from 'react-bootstrap'
import { useSceneLive } from '@/hooks/scene/useSceneLiveQueries'
import QueryState from '@/components/common/QueryState'
import StatusChip from '@/components/common/StatusChip'
import { parseNaiveUtcEpoch } from '@/utils/dateUtils'
import { formatDurationHoursMinutes } from '@/utils/numberUtils'

// Freshness horizon for the "tracker stale" warning. Samples land every ~5 min;
// if the newest sample overall is older than this, the tracker is likely down,
// which reads as "nobody live" — surface that instead of a false empty state.
const STALE_MS = 15 * 60 * 1000

/**
 * Human uptime "2h 14m" / "43m" from a live session start, or null when unknown
 * or the clock is skewed (negative elapsed).
 * @param {string|null} startedAt
 * @returns {string|null}
 */
const uptimeLabel = startedAt => {
    const start = parseNaiveUtcEpoch(startedAt)
    if (start === null) {
        return null
    }
    const elapsedMs = Date.now() - start
    if (elapsedMs < 0) {
        return null
    }
    return formatDurationHoursMinutes(elapsedMs / 1000)
}

/**
 * One live streamer card: avatar, identity, LIVE chip, viewer count, title,
 * uptime. Nullable fields (title/profileImageUrl/sessionStartedAt) are hidden
 * rather than faked per the nullable = unknown contract.
 *
 * @param {object} props
 * @param {object} props.streamer mapped live entry from useSceneLive
 */
const LiveCard = ({ streamer }) => {
    const {
        creatorId,
        nick,
        displayName,
        profileImageUrl,
        viewerCount,
        title,
        sessionStartedAt,
    } = streamer

    const name = displayName || nick
    const uptime = uptimeLabel(sessionStartedAt)

    return (
        <Card className="live-card">
            <Card.Body>
                <div className="live-card-head">
                    {profileImageUrl
                        ? (
                            <Image
                                className="live-avatar"
                                src={profileImageUrl}
                                alt=""
                                width={48}
                                height={48}
                            />
                        )
                        : (
                            <span
                                className="live-avatar live-avatar-empty"
                                aria-hidden="true" />
                        )}
                    <div className="live-identity">
                        <Link className="live-name" href={`/creator/${creatorId}`}>{name}</Link>
                        <StatusChip
                            variant="ok"
                            className="live-chip"
                            aria-label="Live now">
                            LIVE
                        </StatusChip>
                    </div>
                </div>

                <div className="live-metrics">
                    <span className="live-viewers mono">
                        {viewerCount == null ? '--' : viewerCount.toLocaleString()}
                        <span className="live-viewers-unit"> viewers</span>
                    </span>
                    {uptime ? (
                        <span className="live-uptime mono">
                            <i
                                className="bi bi-clock"
                                aria-hidden="true" />
                            {uptime}
                        </span>
                    ) : null}
                </div>

                {title ? (
                    <p
                        className="live-title"
                        title={title}>
                        {title}
                    </p>
                ) : null}
            </Card.Body>
        </Card>
    )
}

/**
 * Live-now dashboard: every tracked streamer whose viewer samples are fresh.
 * Liveness is inferred from sample freshness, so a dead tracker looks like an
 * empty scene — `lastSampleAt` drives a staleness warning to disambiguate.
 * Polls every 30s via the hook's refetchInterval.
 */
const LiveNow = () => {
    const {
        data,
        isLoading,
        error,
        refetch,
    } = useSceneLive()

    const live = data?.live || []

    const lastSampleAt = data?.lastSampleAt ?? null

    const isStale = useMemo(() => {
        const last = parseNaiveUtcEpoch(lastSampleAt)
        // A freshness warning intentionally compares the newest sample with the
        // wall clock; the query's 30-second polling supplies bounded rerenders.
        // eslint-disable-next-line react-hooks/purity
        return last !== null && Date.now() - last > STALE_MS
    }, [
        lastSampleAt,
    ])

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Live now</h1>
                    <p className="page-sub">Tracked streamers broadcasting right now</p>
                </div>
                {live.length > 0 && (
                    <span className="toolbar-readout">
                        <strong>{live.length}</strong> live
                    </span>
                )}
            </div>

            <QueryState
                query={{
                    data, isLoading, error, refetch,
                }}
                errorTitle="Failed to load live streamers"
                loadingText="Checking who's live..."
                loadingSize="md"
                isEmpty={value => (value?.live || []).length === 0}
                emptyState={(
                    <div className="empty-state">
                        <span
                            className="empty-scope"
                            aria-hidden="true" />
                        <p className="empty-title">Nobody live right now</p>
                        {isStale ? (
                            <p className="empty-hint text-warning">
                                Tracking data is stale — the newest viewer sample is over 15 minutes old,
                                so the tracker may be down rather than the scene being quiet.
                            </p>
                        ) : (
                            <p className="empty-hint">
                                No tracked streamer is broadcasting. This refreshes automatically every 30 seconds.
                            </p>
                        )}
                    </div>
                )}
            >
                {value => (
                    <>
                        {isStale && (
                            <p className="live-stale-note text-warning mono">
                                <i
                                    className="bi bi-exclamation-triangle"
                                    aria-hidden="true" />
                                {' '}
                                Latest sample is over 15 minutes old — this list may be incomplete.
                            </p>
                        )}
                        <div className="live-grid">
                            {(value.live || []).map(streamer => (
                                <LiveCard
                                    key={streamer.creatorId}
                                    streamer={streamer}
                                />
                            ))}
                        </div>
                    </>
                )}
            </QueryState>
        </>
    )
}

export default LiveNow
