'use client'

import Link from 'next/link'
import Image from 'next/image'
import { Card } from 'react-bootstrap'
import StatusChip from '@/components/common/StatusChip'
import RadarSparkline from '@/components/scene/RadarSparkline'
import type { RadarChannel } from '@/hooks/scene/useSceneRadarQuery'
import { parseNaiveUtcEpoch } from '@/utils/dateUtils'
import { formatCompactNumber, formatDurationHoursMinutes } from '@/utils/numberUtils'

type SpikeBadgeVariant = 'ok' | 'warn' | 'err' | 'neutral'

export interface SpikeBadge {
    variant: SpikeBadgeVariant
    label: string
}

/**
 * Decide the velocity badge from the spike flag and baseline ratio:
 *   - spiking            → a red "SPIKING" chip, carrying the ratio when known
 *   - not spiking, ratio → a neutral "xN.N vs usual" context hint
 *   - ratio null         → nothing (never a misleading "x0")
 * Pure so the rule is unit-testable without rendering.
 */
export const spikeBadge = (spiking: boolean, ratio: number | null): SpikeBadge | null => {
    if (spiking) {
        return { variant: 'err', label: ratio != null ? `SPIKING x${ratio.toFixed(1)}` : 'SPIKING' }
    }
    if (ratio != null) {
        return { variant: 'neutral', label: `x${ratio.toFixed(1)} vs usual` }
    }
    return null
}

/**
 * Human uptime "2h 14m" / "43m" from a live session start, or null when unknown
 * or the clock is skewed (negative elapsed). Mirrors LiveNow's uptime logic.
 */
const uptimeLabel = (startedAt: string | null): string | null => {
    const start = parseNaiveUtcEpoch(startedAt)
    if (start === null) return null
    const elapsedMs = Date.now() - start
    if (elapsedMs < 0) return null
    return formatDurationHoursMinutes(elapsedMs / 1000)
}

interface RadarCardProps {
    channel: RadarChannel
}

/**
 * One live channel's velocity card: identity, spike badge, msgs/min headline,
 * and an inline sparkline of the trailing minutes. Nullable fields
 * (title/avatar/started_at/ratio) are hidden rather than faked per the
 * nullable = unknown contract.
 */
const RadarCard = ({ channel }: RadarCardProps) => {
    const {
        creatorId,
        creatorNick,
        creatorDisplayName,
        profileImageUrl,
        streamTitle,
        startedAt,
        messagesLastMinute,
        uniqueChattersLastMinute,
        ratio,
        spiking,
        minutes,
    } = channel

    const name = creatorDisplayName || creatorNick
    const uptime = uptimeLabel(startedAt)
    const badge = spikeBadge(spiking, ratio)

    return (
        <Card className={spiking ? 'live-card radar-card is-spiking' : 'live-card radar-card'}>
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
                        <span className="radar-name-row">
                            <span
                                className="radar-live-dot"
                                aria-hidden="true" />
                            <Link className="live-name" href={`/creator/${creatorId}`}>{name}</Link>
                        </span>
                        {badge ? (
                            <StatusChip
                                variant={badge.variant}
                                className="radar-badge">
                                {badge.label}
                            </StatusChip>
                        ) : null}
                    </div>
                </div>

                <div className="radar-headline">
                    <span className="radar-rate">
                        <span className="radar-rate-value text-phosphor mono">
                            {formatCompactNumber(messagesLastMinute)}
                        </span>
                        <span className="radar-rate-unit">msgs/min</span>
                    </span>
                    <span className="radar-chatters mono">
                        {formatCompactNumber(uniqueChattersLastMinute)}
                        <span className="radar-chatters-unit"> chatters</span>
                    </span>
                </div>

                <RadarSparkline
                    minutes={minutes}
                    spiking={spiking} />

                <div className="radar-foot">
                    {streamTitle ? (
                        <p
                            className="live-title radar-title"
                            title={streamTitle}>
                            {streamTitle}
                        </p>
                    ) : (
                        <p className="live-title radar-title radar-title-empty">—</p>
                    )}
                    {uptime ? (
                        <span className="live-uptime mono">
                            <i
                                className="bi bi-clock"
                                aria-hidden="true" />
                            {uptime}
                        </span>
                    ) : null}
                </div>
            </Card.Body>
        </Card>
    )
}

export default RadarCard
