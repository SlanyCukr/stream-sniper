'use client'
import { useMemo } from 'react'
import { Card } from 'react-bootstrap'
import { useSceneLive } from '@/hooks/useApiQuery'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

// Freshness horizon for the "tracker stale" warning. Samples land every ~5 min;
// if the newest sample overall is older than this, the tracker is likely down,
// which reads as "nobody live" — surface that instead of a false empty state.
const STALE_MS = 15 * 60 * 1000

/**
 * Parse a naive UTC timestamp ("YYYY-MM-DDTHH:MM:SS", no zone) as UTC by
 * appending 'Z' — the backend formats AT TIME ZONE 'UTC' without an offset.
 * @param {string|null} ts
 * @returns {number|null} epoch ms, or null when unparseable
 */
const utcEpoch = ts => {
    if (typeof ts !== 'string' || ts.length < 16) {
        return null
    }
    const ms = new Date(`${ts}Z`).getTime()
    return Number.isNaN(ms) ? null : ms
}

/**
 * Human uptime "2h 14m" / "43m" from a live session start, or null when unknown
 * or the clock is skewed (negative elapsed).
 * @param {string|null} startedAt
 * @returns {string|null}
 */
const uptimeLabel = startedAt => {
    const start = utcEpoch(startedAt)
    if (start === null) {
        return null
    }
    const totalMin = Math.floor((Date.now() - start) / 60000)
    if (totalMin < 0) {
        return null
    }
    const hours = Math.floor(totalMin / 60)
    const minutes = totalMin % 60
    return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`
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
                            <img
                                className="live-avatar"
                                src={profileImageUrl}
                                alt=""
                                width={48}
                                height={48}
                                loading="lazy"
                            />
                        )
                        : (
                            <span
                                className="live-avatar live-avatar-empty"
                                aria-hidden="true" />
                        )}
                    <div className="live-identity">
                        <span className="live-name">{name}</span>
                        <span
                            className="status-chip is-ok live-chip"
                            aria-label="Live now">
                            LIVE
                        </span>
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

    const live = useMemo(() => data?.live || [
    ], [
        data?.live,
    ])

    const lastSampleAt = data?.lastSampleAt ?? null

    const isStale = useMemo(() => {
        const last = utcEpoch(lastSampleAt)
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

            {error ? (
                <ErrorAlert
                    error={error}
                    title="Failed to load live streamers"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : isLoading ? (
                <LoadingSpinner
                    text="Checking who's live..."
                    centered
                />
            ) : live.length === 0 ? (
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
            ) : (
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
                        {live.map(streamer => (
                            <LiveCard
                                key={streamer.creatorId}
                                streamer={streamer}
                            />
                        ))}
                    </div>
                </>
            )}
        </>
    )
}

export default LiveNow
