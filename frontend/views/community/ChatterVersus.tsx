'use client'

import { useState } from 'react'
import Link from 'next/link'
import AsyncSearchSelect from '@/components/common/search/AsyncSearchSelect'
import ArchetypeBadges from '@/components/chatter/ArchetypeBadges'
import QueryState from '@/components/common/QueryState'
import StatusChip from '@/components/common/StatusChip'
import {
    useChatterHeadToHead,
    type ChatterHeadToHead,
    type ChatterVersusSide,
} from '@/hooks/chatter/useChatterVersusQuery'
import {
    loadChatterOptions,
    noOptionsMessage,
    type ChatterOption,
} from '@/hooks/chatter/useChatterExplorer'
import { useVersusPairUrl } from '@/hooks/community/useVersusPairUrl'
import { formatCompactNumber, formatSharePct, shareBarWidth } from '@/utils/numberUtils'
import { formatDateOrDash } from '@/utils/dateUtils'

const SideCard = ({ side }: { side: ChatterVersusSide }) => (
    <div className="versus-side card">
        <div className="chatter-versus-name">
            <Link className="versus-side-name" href={`/chatter/${side.chatterId}`}>
                {side.nick}
            </Link>
            {side.isBot === true ? <StatusChip variant="warn">BOT</StatusChip> : null}
        </div>
        <div className="chatter-versus-badges">
            <ArchetypeBadges archetypes={side.archetypes} />
        </div>
        <div className="versus-side-stats">
            <div className="stat-tile">
                <div className="stat-label">Messages</div>
                <div className="stat-value">{formatCompactNumber(side.messages)}</div>
            </div>
            <div className="stat-tile">
                <div className="stat-label">Streams</div>
                <div className="stat-value">{formatCompactNumber(side.streamsAttended)}</div>
            </div>
            <div className="stat-tile">
                <div className="stat-label">Channels</div>
                <div className="stat-value">{formatCompactNumber(side.creatorsVisited)}</div>
            </div>
        </div>
        {side.homeChannel ? (
            <div className="versus-share">
                <div className="versus-share-label">
                    <span>
                        {'Home: '}
                        <Link href={`/creator/${side.homeChannel.creatorId}`}>
                            {side.homeChannel.creatorDisplayName || side.homeChannel.creatorNick}
                        </Link>
                    </span>
                    <span className="mono">{formatSharePct(side.homeChannel.share)}</span>
                </div>
                <div className="versus-share-track" aria-hidden="true">
                    <div
                        className="versus-share-fill"
                        style={{ width: `${shareBarWidth(side.homeChannel.share)}%` }}
                    />
                </div>
            </div>
        ) : null}
        <p className="chatter-versus-era">
            {`Active ${formatDateOrDash(side.firstSeen)} → ${formatDateOrDash(side.lastSeen)}`}
        </p>
    </div>
)

interface VersusResultProps {
    data: ChatterHeadToHead
    /** Chatter id picked on the left, so display order follows the pickers, not the normalized payload. */
    leftId: number
}

const VersusResult = ({ data, leftId }: VersusResultProps) => {
    // The payload is normalized (side `a` = lower id); re-orient it to the pickers.
    const [left, right] = data.a.chatterId === leftId ? [data.a, data.b] : [data.b, data.a]
    return (
        <div className="versus-grid">
            <SideCard side={left} />
            <div className="versus-center card">
                <div className="versus-vs" aria-hidden="true">vs</div>
                <div className="stat-tile">
                    <div className="stat-label">Shared streams</div>
                    <div className="stat-value">{formatCompactNumber(data.sharedStreams)}</div>
                </div>
                <div className="stat-tile">
                    <div className="stat-label">Shared channels</div>
                    <div className="stat-value">{formatCompactNumber(data.sharedCreators)}</div>
                </div>
            </div>
            <SideCard side={right} />
        </div>
    )
}

interface ChatterVersusProps {
    initialA?: number | null
    initialB?: number | null
}

const ChatterVersus = ({ initialA = null, initialB = null }: ChatterVersusProps) => {
    // Deep-linked ids arrive without nicks; the pickers show a plain #id label
    // until the user changes them (the comparison itself only needs the id).
    const [pickA, setPickA] = useState<ChatterOption | null>(
        initialA ? { value: initialA, label: `#${initialA}`, isBot: null } : null,
    )
    const [pickB, setPickB] = useState<ChatterOption | null>(
        initialB ? { value: initialB, label: `#${initialB}`, isBot: null } : null,
    )
    const syncPairUrl = useVersusPairUrl()

    const pickChatter = (side: 'a' | 'b', option: ChatterOption | null) => {
        const nextA = side === 'a' ? option : pickA
        const nextB = side === 'b' ? option : pickB
        if (side === 'a') setPickA(option)
        else setPickB(option)
        syncPairUrl(nextA?.value ?? null, nextB?.value ?? null)
    }

    const chatterA = pickA?.value ?? null
    const chatterB = pickB?.value ?? null
    const samePick = chatterA !== null && chatterA === chatterB
    const query = useChatterHeadToHead(chatterA, chatterB)

    return (
        <>
            <header className="page-head">
                <div>
                    <p className="page-sub">two chatters, side by side</p>
                    <h1 className="page-title">Chatter versus</h1>
                </div>
                <Link className="btn btn-outline-secondary btn-sm" href="/versus">
                    Creator versus →
                </Link>
            </header>
            <div className="toolbar versus-toolbar">
                <AsyncSearchSelect
                    instanceId="chatter-versus-a"
                    inputId="chatter-versus-a-input"
                    loadOptions={loadChatterOptions}
                    value={pickA}
                    onChange={(newValue: unknown) => pickChatter('a', newValue as ChatterOption | null)}
                    noOptionsMessage={noOptionsMessage}
                    placeholder="First chatter..."
                    isClearable
                    aria-label="First chatter"
                />
                <span className="versus-toolbar-vs" aria-hidden="true">vs</span>
                <AsyncSearchSelect
                    instanceId="chatter-versus-b"
                    inputId="chatter-versus-b-input"
                    loadOptions={loadChatterOptions}
                    value={pickB}
                    onChange={(newValue: unknown) => pickChatter('b', newValue as ChatterOption | null)}
                    noOptionsMessage={noOptionsMessage}
                    placeholder="Second chatter..."
                    isClearable
                    aria-label="Second chatter"
                />
            </div>
            {chatterA === null || chatterB === null ? (
                <div className="empty-state">
                    <p className="empty-title">Pick two chatters</p>
                    <p className="empty-hint">
                        Compare lifetime footprints — messages, streams, home channels, and how often they crossed paths.
                    </p>
                </div>
            ) : null}
            {samePick ? (
                <div className="empty-state">
                    <p className="empty-title">Same chatter on both sides</p>
                    <p className="empty-hint">Pick two different chatters to compare.</p>
                </div>
            ) : null}
            <QueryState
                query={query}
                errorTitle="Chatter versus unavailable"
                loadingText="Weighing the chat logs..."
                emptyState={null}
                showErrorDetails={false}
            >
                {(data: ChatterHeadToHead) => (
                    <VersusResult data={data} leftId={chatterA as number} />
                )}
            </QueryState>
        </>
    )
}

export default ChatterVersus
