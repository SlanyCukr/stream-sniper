'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import Select from 'react-select'
import { Card } from 'react-bootstrap'
import { useAudienceMovement, type AudienceAssociation } from '@/hooks/creator/useAudienceMovementQuery'
import {
    mapCreatorOption, useCreators,
} from '@/hooks/creator/useCreatorsQuery'
import EmptyState from '@/components/common/EmptyState'
import FilterPills from '@/components/common/FilterPills'
import QueryState from '@/components/common/QueryState'

const WINDOWS = [7, 30, 90]

interface AssociationListProps {
    title: string
    items: AudienceAssociation[]
    empty: string
}

const AssociationList = ({ title, items, empty }: AssociationListProps) => (
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

interface AudienceMovementProps {
    initialCreatorId?: number | null
}

const AudienceMovement = ({ initialCreatorId = null }: AudienceMovementProps) => {
    const [creatorId, setCreatorId] = useState<number | null>(initialCreatorId)
    const [days, setDays] = useState(30)
    const creatorsQuery = useCreators()
    const options = useMemo(
        () => (creatorsQuery.data || []).map(mapCreatorOption),
        [creatorsQuery.data],
    )
    const selected = options.find(option => option.value === creatorId) || null
    // useAudienceMovement's own `enabled: Boolean(creatorId)` gate is what makes
    // a null creatorId safe at runtime even though its param type is `number`.
    const query = useAudienceMovement(creatorId as number, { days })

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
                <FilterPills
                    options={WINDOWS.map(window => ({ key: window, label: `${window} days` }))}
                    activeKey={days}
                    ariaLabel="Movement window"
                    onChange={setDays}
                />
            </div>
            {!creatorId ? (
                <EmptyState title="Choose a creator">
                    Compare distinct chat participants with the preceding equal window.
                </EmptyState>
            ) : null}
            <QueryState
                query={query}
                errorTitle="Movement report failed"
                loadingText="Following audience participation..."
                emptyState={null}
                showErrorDetails={false}
            >
                {data => (
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
                )}
            </QueryState>
        </>
    )
}

export default AudienceMovement
