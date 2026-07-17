'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Card } from 'react-bootstrap'
import { useSceneDigest, useScenePulse } from '@/hooks/scene/useScenePulseQueries'
import QueryState from '@/components/common/QueryState'
import { formatTimeAgo } from '@/utils/dateUtils'

const FILTERS = [
    ['', 'Everything'],
    ['personal_record', 'Records'],
    ['standout_moment', 'Moments'],
    ['copypasta_spread', 'Copypastas'],
    ['stream_report', 'Streams'],
]

const icon = type => ({
    personal_record: 'bi-trophy',
    standout_moment: 'bi-lightning',
    copypasta_spread: 'bi-chat-quote',
    stream_report: 'bi-broadcast',
}[type] || 'bi-activity')

const ScenePulse = () => {
    const [eventType, setEventType] = useState('')
    const [days, setDays] = useState(7)
    const [copied, setCopied] = useState(false)
    const pulse = useScenePulse({ days, eventType: eventType || undefined, limit: 100 })
    const digest = useSceneDigest({ days })

    const copyDigest = async () => {
        await navigator.clipboard.writeText(digest.data || '')
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1500)
    }

    return (
        <>
            <header className="page-head">
                <div>
                    <p className="page-sub">
                        what changed across the captured scene
                    </p>
                    <h1 className="page-title">
                        Scene pulse
                    </h1>
                </div>
                <button
                    type="button"
                    className="btn btn-outline-primary btn-sm"
                    disabled={!digest.data}
                    onClick={copyDigest}
                >
                    {copied ? 'Copied' : 'Copy digest'}
                </button>
            </header>
            <div className="toolbar pulse-toolbar">
                <div
                    className="chatter-tabs"
                    role="tablist"
                    aria-label="Event type"
                >
                    {FILTERS.map(([value, label]) => (
                        <button
                            key={value}
                            type="button"
                            role="tab"
                            aria-selected={eventType === value}
                            className={eventType === value ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setEventType(value)}
                        >
                            {label}
                        </button>
                    ))}
                </div>
                <select
                    className="form-select form-select-sm"
                    value={days}
                    onChange={event => setDays(Number(event.target.value))}
                >
                    <option value="1">24 hours</option>
                    <option value="7">7 days</option>
                    <option value="30">30 days</option>
                    <option value="90">90 days</option>
                </select>
            </div>
            <QueryState
                query={pulse}
                errorTitle="Scene pulse failed"
                loadingText="Reading the scene..."
                isEmpty={value => !(value?.items?.length)}
                emptyState={(
                    <div className="empty-state">
                        <p className="empty-title">
                            No events yet
                        </p>
                        <p className="empty-hint">
                            Re-run stream rollups to populate deterministic scene events.
                        </p>
                    </div>
                )}
                showErrorDetails={false}
            >
                {value => (
                    <div className="pulse-feed">
                        {(value.items || []).map(event => (
                            <Card
                                key={event.id}
                                className={`pulse-event pulse-${event.eventType}`}
                            >
                                <Card.Body>
                                    <div className="pulse-icon">
                                        <i
                                            className={`bi ${icon(event.eventType)}`}
                                            aria-hidden="true"
                                        />
                                    </div>
                                    <div className="pulse-content">
                                        <div className="mono text-muted">
                                            {`${formatTimeAgo(event.occurredAt)} · ${event.eventType.replaceAll('_', ' ')}`}
                                        </div>
                                        <h2>{event.title}</h2>
                                        <p>{event.summary}</p>
                                        <div className="pulse-links">
                                            {event.creatorId ? (
                                                <Link href={`/creator/${event.creatorId}`}>
                                                    Creator dossier
                                                </Link>
                                            ) : null}
                                            {event.streamId ? (
                                                <Link href={`/stream/${event.streamId}`}>
                                                    Stream
                                                </Link>
                                            ) : null}
                                            {event.messageTextId ? (
                                                <Link href={`/copypasta/${event.messageTextId}`}>
                                                    Trace copypasta
                                                </Link>
                                            ) : null}
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        ))}
                    </div>
                )}
            </QueryState>
        </>
    )
}

export default ScenePulse
