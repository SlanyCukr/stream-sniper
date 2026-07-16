'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import Select from 'react-select'
import { Card } from 'react-bootstrap'
import { useAudienceMovement } from '@/hooks/creator/useAudienceMovementQuery'
import {
    mapCreatorOption, useCreators,
} from '@/hooks/creator/useCreatorsQuery'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'

const WINDOWS = [7, 30, 90]

const AssociationList = ({ title, items, empty }) => (
    <Card>
        <Card.Body>
            <div className="section-label">
                {title}
            </div>
            {items.length ? (
                <ol className="rank-list">
                    {items.map((item, index) => (
                        <li key={item.creatorId}>
                            <span className="rank">
                                {String(index + 1).padStart(2, '0')}
                            </span>
                            <Link
                                className="nick"
                                href={`/creator/${item.creatorId}`}
                            >
                                {item.displayName || item.nick}
                            </Link>
                            <span className="count">
                                {item.chatterCount}
                            </span>
                        </li>
                    ))}
                </ol>
            ) : (
                <p className="text-muted mt-3">
                    {empty}
                </p>
            )}
        </Card.Body>
    </Card>
)

/** @param {{initialCreatorId?: number|null}} props */
const AudienceMovement = ({ initialCreatorId = null }) => {
    const [creatorId, setCreatorId] = useState(initialCreatorId)
    const [days, setDays] = useState(30)
    const creatorsQuery = useCreators()
    const options = useMemo(
        () => (creatorsQuery.data || []).map(mapCreatorOption),
        [creatorsQuery.data],
    )
    const selected = options.find(option => option.value === creatorId) || null
    const query = useAudienceMovement(creatorId, { days })
    const data = query.data

    return (
        <>
            <header className="page-head">
                <div>
                    <p className="page-sub">
                        participation change, not causal migration
                    </p>
                    <h1 className="page-title">
                        Audience movement
                    </h1>
                </div>
            </header>
            <div className="toolbar movement-toolbar">
                <Select
                    classNamePrefix="rs"
                    instanceId="movement-creator"
                    options={options}
                    value={selected}
                    onChange={option => setCreatorId(option?.value || null)}
                    placeholder="Choose creator..."
                />
                <div
                    className="chatter-tabs"
                    role="tablist"
                    aria-label="Movement window"
                >
                    {WINDOWS.map(window => (
                        <button
                            key={window}
                            type="button"
                            role="tab"
                            aria-selected={days === window}
                            className={days === window ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setDays(window)}
                        >
                            {`${window} days`}
                        </button>
                    ))}
                </div>
            </div>
            {!creatorId ? (
                <div className="empty-state">
                    <p className="empty-title">
                        Choose a creator
                    </p>
                    <p className="empty-hint">
                        Compare distinct chat participants with the preceding equal window.
                    </p>
                </div>
            ) : null}
            {query.isLoading ? (
                <LoadingSpinner
                    size="lg"
                    text="Following audience participation..."
                />
            ) : null}
            {query.error ? (
                <ErrorAlert
                    title="Movement report failed"
                    error={query.error}
                    onRetry={query.refetch}
                />
            ) : null}
            {data ? (
                <>
                    <div
                        className="stats-strip"
                        role="list"
                    >
                        {[
                            ['Current audience', data.currentAudience],
                            ['Previous audience', data.previousAudience],
                            ['Retained', data.retained],
                            ['Gained', data.gained],
                            ['Lapsed', data.lapsed],
                            ['Retention', data.retentionRate == null ? '--' : `${Math.round(data.retentionRate * 100)}%`],
                        ].map(([label, value]) => (
                            <div
                                className="stat-tile"
                                role="listitem"
                                key={label}
                            >
                                <div className="stat-label">
                                    {label}
                                </div>
                                <div className="stat-value">
                                    {typeof value === 'number' ? value.toLocaleString() : value}
                                </div>
                            </div>
                        ))}
                    </div>
                    <p className="movement-caveat">
                        Associations below mean the same chatters participated in those channels during the adjacent window. They do not prove that viewers moved because of a creator.
                    </p>
                    <div className="dossier-grid">
                        <AssociationList
                            title="Earlier channels for gained chatters"
                            items={data.priorChannelsForGained}
                            empty="No earlier cross-channel activity found."
                        />
                        <AssociationList
                            title="Current channels for lapsed chatters"
                            items={data.currentChannelsForLapsed}
                            empty="No current cross-channel activity found."
                        />
                    </div>
                </>
            ) : null}
        </>
    )
}

export default AudienceMovement
