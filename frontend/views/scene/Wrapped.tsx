'use client'

import { useState } from 'react'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import TabList from '@/components/common/TabList'
import WrappedRecap from '@/components/scene/WrappedRecap'
import {
    useSceneWrapped,
    isWrappedEmpty,
    type SceneWrapped,
} from '@/hooks/scene/useSceneWrappedQuery'

const DAYS_TABS: Array<{ key: number, label: string }> = [
    { key: 7, label: '7 days' },
    { key: 30, label: '30 days' },
    { key: 90, label: '90 days' },
]

const Wrapped = () => {
    const [days, setDays] = useState(30)
    const query = useSceneWrapped(days)

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">the scene, condensed</p>
                    <h1 className="page-title">Scene Wrapped</h1>
                </div>
            </div>

            <div
                className="toolbar scene-toolbar wrapped-toolbar"
                role="search"
                aria-label="Recap window"
            >
                <TabList
                    tabs={DAYS_TABS}
                    activeKey={days}
                    idPrefix="wrapped-window"
                    ariaLabel="Window"
                    onChange={setDays}
                />
            </div>

            <div
                id={`wrapped-window-panel-${days}`}
                role="tabpanel"
                aria-labelledby={`wrapped-window-tab-${days}`}
            >
                <QueryState
                    query={query}
                    errorTitle="Failed to load the scene recap"
                    loadingText="Wrapping the scene..."
                    isEmpty={(value: SceneWrapped) => isWrappedEmpty(value)}
                    emptyState={(
                        <EmptyState title="Nothing to wrap yet">
                            No scene activity landed inside this window yet.
                        </EmptyState>
                    )}
                >
                    {(data: SceneWrapped) => <WrappedRecap wrapped={data} />}
                </QueryState>
            </div>
        </>
    )
}

export default Wrapped
