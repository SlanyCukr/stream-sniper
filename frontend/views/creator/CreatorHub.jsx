'use client'

import { useCreatorHub } from '@/hooks/creator/useCreatorHub'
import CreatorHubControls from '@/components/creator/CreatorHubControls'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import RegularsPanel from '@/components/creator/RegularsPanel'
import TrendsPanel from '@/components/creator/TrendsPanel'

const CreatorHub = ({ initialView = 'regulars' }) => {
    const hub = useCreatorHub(initialView)

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Creators</h1>
                    <p className="page-sub">Per-stream trends and recurring chatters for a creator</p>
                </div>
            </div>
            {hub.creatorsQuery.error ? (
                <ErrorAlert
                    error={hub.creatorsQuery.error}
                    title="Failed to load creators"
                    onRetry={hub.creatorsQuery.refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : null}
            <CreatorHubControls
                options={hub.options}
                selectedCreator={hub.selectedCreator}
                view={hub.view}
                onCreatorChange={hub.setSelectedCreator}
                onViewChange={hub.setView}
            />
            <div id={`creator-panel-${hub.view}`} role="tabpanel" aria-labelledby={`creator-tab-${hub.view}`}>
                {hub.view === 'trends'
                    ? <TrendsPanel creatorId={hub.creatorId} />
                    : <RegularsPanel creatorId={hub.creatorId} />}
            </div>
        </>
    )
}

export default CreatorHub
