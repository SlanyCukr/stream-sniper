'use client'

import { useCreatorEmotes } from '@/hooks/stream/insights/useStreamInsightsQuery'
import { useCreatorNeighbors } from '@/hooks/community/useCommunityQuery'
import { useCreatorSummary } from '@/hooks/creator/useCreatorSummaryQuery'
import { useSceneCopypastas } from '@/hooks/scene/useSceneCopypastaQueries'
import CreatorDossierOverview from '@/components/creator/CreatorDossierOverview'
import CreatorSignatureCards from '@/components/creator/CreatorSignatureCards'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import QueryState from '@/components/common/QueryState'
import RegularsPanel from '@/components/creator/RegularsPanel'
import TrendsPanel from '@/components/creator/TrendsPanel'

const CreatorDossier = ({ creatorId }) => {
    const summaryQuery = useCreatorSummary(creatorId)
    const emotesQuery = useCreatorEmotes(creatorId, { limit: 8 })
    const neighborsQuery = useCreatorNeighbors(creatorId, { metric: 'regulars', limit: 6 })
    const copypastasQuery = useSceneCopypastas({ creatorId, sort: 'usage', pageSize: 5 })

    if (!Number.isInteger(creatorId) || creatorId <= 0) {
        return <ErrorAlert title="Invalid creator" error={new Error('Creator ID must be a positive integer.')} />
    }

    return (
        <QueryState
            query={summaryQuery}
            errorTitle="Failed to load creator"
            loadingText="Building creator dossier..."
            showErrorDetails={false}
        >
            {creator => (
                <>
                    <CreatorDossierOverview creator={creator} creatorId={creatorId} />
                    <section className="dossier-section">
                        <div className="section-label">Recent trajectory</div>
                        <TrendsPanel creatorId={creatorId} />
                    </section>
                    <CreatorSignatureCards
                        emotesQuery={emotesQuery}
                        neighborsQuery={neighborsQuery}
                        copypastasQuery={copypastasQuery}
                    />
                    <section className="dossier-section">
                        <div className="section-label">Core regulars</div>
                        <RegularsPanel creatorId={creatorId} />
                    </section>
                </>
            )}
        </QueryState>
    )
}

export default CreatorDossier
