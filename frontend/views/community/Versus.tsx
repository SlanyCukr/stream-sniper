'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import Select from 'react-select'
import QueryState from '@/components/common/QueryState'
import { useCreatorHeadToHead, type CreatorHeadToHead, type HeadToHeadSide } from '@/hooks/community/useHeadToHeadQuery'
import { mapCreatorOption, useCreators } from '@/hooks/creator/useCreatorsQuery'
import { formatDate } from '@/utils/dateUtils'
import { shareBarWidth } from '@/utils/numberUtils'

const formatShare = (share: number | null): string => (
    share === null ? '—' : `${(share * 100).toFixed(1)}%`
)

const formatJaccard = (value: number | null): string => (
    value === null ? '—' : `${(value * 100).toFixed(1)}%`
)

interface SideCardProps {
    side: HeadToHeadSide
    /** Which overlap metric the share bars visualize. */
    metricLabel: 'chatters' | 'regulars'
}

const SideCard = ({ side, metricLabel }: SideCardProps) => {
    const share = metricLabel === 'chatters' ? side.sharedChatterShare : side.sharedRegularShare
    return (
        <div className="versus-side card">
            <Link className="versus-side-name" href={`/creator/${side.creatorId}`}>
                {side.displayName || side.nick}
            </Link>
            <div className="versus-side-stats">
                <div className="stat-tile">
                    <div className="stat-label">Chatters</div>
                    <div className="stat-value">{side.chatters.toLocaleString()}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Regulars</div>
                    <div className="stat-value">{side.regulars.toLocaleString()}</div>
                </div>
            </div>
            <div className="versus-share">
                <div className="versus-share-label">
                    <span>{`Audience shared (${metricLabel})`}</span>
                    <span className="mono">{formatShare(share)}</span>
                </div>
                <div className="versus-share-track" aria-hidden="true">
                    <div
                        className="versus-share-fill"
                        style={{ width: `${share === null ? 0 : shareBarWidth(share)}%` }}
                    />
                </div>
            </div>
        </div>
    )
}

interface VersusResultProps {
    data: CreatorHeadToHead
    /** Creator id picked on the left, so the display order follows the pickers, not the normalized payload. */
    leftId: number
    metric: 'chatters' | 'regulars'
}

const VersusResult = ({ data, leftId, metric }: VersusResultProps) => {
    // The payload is normalized (side `a` = lower id); re-orient it to the pickers.
    const [left, right] = data.a.creatorId === leftId ? [data.a, data.b] : [data.b, data.a]
    return (
        <>
            <div className="versus-grid">
                <SideCard side={left} metricLabel={metric} />
                <div className="versus-center card">
                    <div className="versus-vs" aria-hidden="true">vs</div>
                    <div className="stat-tile">
                        <div className="stat-label">Shared chatters</div>
                        <div className="stat-value">{data.sharedChatters.toLocaleString()}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Shared regulars</div>
                        <div className="stat-value">{data.sharedRegulars.toLocaleString()}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Jaccard (chatters)</div>
                        <div className="stat-value">{formatJaccard(data.jaccardChatters)}</div>
                    </div>
                    <div className="stat-tile">
                        <div className="stat-label">Jaccard (regulars)</div>
                        <div className="stat-value">{formatJaccard(data.jaccardRegulars)}</div>
                    </div>
                </div>
                <SideCard side={right} metricLabel={metric} />
            </div>
            {data.computedAt ? (
                <p className="versus-computed">
                    {`Overlap rollup computed ${formatDate(data.computedAt, 'MMM d, yyyy HH:mm')} UTC.`}
                </p>
            ) : null}
        </>
    )
}

interface VersusProps {
    initialA?: number | null
    initialB?: number | null
}

const Versus = ({ initialA = null, initialB = null }: VersusProps) => {
    const [creatorA, setCreatorA] = useState<number | null>(initialA)
    const [creatorB, setCreatorB] = useState<number | null>(initialB)
    const [metric, setMetric] = useState<'chatters' | 'regulars'>('chatters')
    const router = useRouter()
    const pathname = usePathname()

    const creatorsQuery = useCreators()
    const options = useMemo(
        () => (creatorsQuery.data || []).map(mapCreatorOption),
        [creatorsQuery.data],
    )
    const selectedA = options.find(option => option.value === creatorA) || null
    const selectedB = options.find(option => option.value === creatorB) || null

    const pickCreator = (side: 'a' | 'b', value: number | null) => {
        const nextA = side === 'a' ? value : creatorA
        const nextB = side === 'b' ? value : creatorB
        if (side === 'a') setCreatorA(value)
        else setCreatorB(value)
        // Keep the matchup deep-linkable without triggering a navigation/remount.
        const params = new URLSearchParams()
        if (nextA) params.set('a', String(nextA))
        if (nextB) params.set('b', String(nextB))
        const query = params.toString()
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    }

    const samePick = creatorA !== null && creatorA === creatorB
    const query = useCreatorHeadToHead(creatorA, creatorB)

    return (
        <>
            <header className="page-head">
                <div>
                    <p className="page-sub">
                        shared audience, side by side
                    </p>
                    <h1 className="page-title">
                        Head-to-head
                    </h1>
                </div>
                <Link className="btn btn-outline-secondary btn-sm" href="/versus/chatters">
                    Chatter versus →
                </Link>
            </header>
            <div className="toolbar versus-toolbar">
                <Select
                    classNamePrefix="rs"
                    instanceId="versus-creator-a"
                    options={options}
                    value={selectedA}
                    onChange={option => pickCreator('a', option?.value || null)}
                    placeholder="First creator..."
                    aria-label="First creator"
                />
                <span className="versus-toolbar-vs" aria-hidden="true">vs</span>
                <Select
                    classNamePrefix="rs"
                    instanceId="versus-creator-b"
                    options={options}
                    value={selectedB}
                    onChange={option => pickCreator('b', option?.value || null)}
                    placeholder="Second creator..."
                    aria-label="Second creator"
                />
                <div
                    className="chatter-tabs"
                    role="tablist"
                    aria-label="Share metric"
                >
                    {(['chatters', 'regulars'] as const).map(option => (
                        <button
                            key={option}
                            type="button"
                            role="tab"
                            aria-selected={metric === option}
                            className={metric === option ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => setMetric(option)}
                        >
                            {option}
                        </button>
                    ))}
                </div>
            </div>
            {!creatorA || !creatorB ? (
                <div className="empty-state">
                    <p className="empty-title">
                        Pick two creators
                    </p>
                    <p className="empty-hint">
                        See how much of their audiences overlap — shared chatters, regulars, and each side&apos;s share.
                    </p>
                </div>
            ) : null}
            {samePick ? (
                <div className="empty-state">
                    <p className="empty-title">
                        Same creator on both sides
                    </p>
                    <p className="empty-hint">
                        Pick two different creators to compare.
                    </p>
                </div>
            ) : null}
            <QueryState
                query={query}
                errorTitle="Head-to-head unavailable"
                loadingText="Weighing the audiences..."
                emptyState={null}
                showErrorDetails={false}
            >
                {(data: CreatorHeadToHead) => (
                    <VersusResult
                        data={data}
                        leftId={creatorA as number}
                        metric={metric}
                    />
                )}
            </QueryState>
        </>
    )
}

export default Versus
