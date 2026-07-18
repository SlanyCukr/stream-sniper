'use client'

import { useState } from 'react'
import Link from 'next/link'
import QueryState from '@/components/common/QueryState'
import EmptyState from '@/components/common/EmptyState'
import FilterPills from '@/components/common/FilterPills'
import CreatorWrappedRecap from '@/components/creator/CreatorWrappedRecap'
import {
    useCreatorWrapped,
    isCreatorWrappedEmpty,
    type CreatorWrapped as CreatorWrappedData,
} from '@/hooks/creator/useCreatorWrappedQuery'

const DAYS_TABS: Array<{ key: number, label: string }> = [
    { key: 7, label: '7 days' },
    { key: 30, label: '30 days' },
    { key: 90, label: '90 days' },
]

const CreatorWrapped = ({ creatorId }: { creatorId: number }) => {
    const [days, setDays] = useState(30)
    const query = useCreatorWrapped(creatorId, days)

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">this creator, condensed</p>
                    <h1 className="page-title">Creator Wrapped</h1>
                </div>
                <Link className="btn btn-outline-primary btn-sm" href={`/creator/${creatorId}`}>
                    Back to dossier
                </Link>
            </div>

            <div
                className="toolbar scene-toolbar wrapped-toolbar"
                role="search"
                aria-label="Recap window"
            >
                <FilterPills
                    options={DAYS_TABS}
                    activeKey={days}
                    ariaLabel="Window"
                    onChange={setDays}
                />
            </div>

            <QueryState
                query={query}
                errorTitle="Failed to load the creator recap"
                loadingText="Wrapping this creator's window..."
                isEmpty={(value: CreatorWrappedData) => isCreatorWrappedEmpty(value)}
                emptyState={(
                    <EmptyState title="Nothing to wrap yet">
                        No activity landed inside this window yet.
                    </EmptyState>
                )}
            >
                {(data: CreatorWrappedData) => <CreatorWrappedRecap wrapped={data} />}
            </QueryState>
        </>
    )
}

export default CreatorWrapped
