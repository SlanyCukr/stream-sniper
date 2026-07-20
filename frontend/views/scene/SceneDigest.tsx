'use client'

import { useState } from 'react'
import { useCopyToClipboard } from '@/hooks/useCopyToClipboard'
import DigestMarkdown from '@/components/scene/DigestMarkdown'
import FilterPills from '@/components/common/FilterPills'
import QueryState from '@/components/common/QueryState'
import { useSceneDigest } from '@/hooks/scene/useScenePulseQueries'

const WINDOW_TABS: Array<{ key: number, label: string }> = [
    { key: 7, label: '7 days' },
    { key: 14, label: '14 days' },
    { key: 30, label: '30 days' },
]

/**
 * The web mirror of the Discord scene digest: the same markdown payload the
 * weekly webhook delivers, rendered as a page with a window selector and a
 * copy button (for pasting into chats that don't get the webhook).
 */
const SceneDigest = () => {
    const [days, setDays] = useState(7)
    const { copied, copy } = useCopyToClipboard()
    const query = useSceneDigest({ days })

    const copyDigest = () => {
        if (query.data) void copy(query.data)
    }

    return (
        <>
            <header className="page-head">
                <div>
                    <p className="page-sub">the scene, summarized</p>
                    <h1 className="page-title">Digest</h1>
                </div>
                <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={copyDigest}
                    disabled={!query.data}
                >
                    {copied ? 'Copied' : 'Copy as markdown'}
                </button>
            </header>
            <div className="toolbar" role="search" aria-label="Digest controls">
                <span className="toolbar-label">Window</span>
                <FilterPills
                    options={WINDOW_TABS}
                    activeKey={days}
                    ariaLabel="Digest window"
                    onChange={setDays}
                />
            </div>
            <section className="card digest-card">
                <QueryState
                    query={query}
                    errorTitle="Digest unavailable"
                    loadingText="Compiling the scene digest…"
                    isEmpty={(markdown: string) => !markdown.trim()}
                    emptyTitle="Nothing to report"
                    emptyHint={`No notable scene activity in the last ${days} days.`}
                >
                    {(markdown: string) => <DigestMarkdown markdown={markdown} />}
                </QueryState>
            </section>
        </>
    )
}

export default SceneDigest
