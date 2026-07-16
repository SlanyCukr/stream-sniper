'use client'

import { useCreatorEmotes } from '@/hooks/stream/insights/useStreamInsightsQuery'
import { useCreatorNeighbors } from '@/hooks/community/useCommunityQuery'
import { useCreatorSummary } from '@/hooks/creator/useCreatorSummaryQuery'
import { useSceneCopypastas } from '@/hooks/scene/useSceneCopypastaQueries'
import CreatorDossierOverview from '@/components/creator/CreatorDossierOverview'
import CreatorSignatureCards from '@/components/creator/CreatorSignatureCards'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
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
    if (summaryQuery.isLoading) return <LoadingSpinner size="lg" text="Building creator dossier..." />
    if (summaryQuery.error) {
        return <ErrorAlert title="Failed to load creator" error={summaryQuery.error} onRetry={summaryQuery.refetch} />
    }

    return (
        <>
            <CreatorDossierOverview creator={summaryQuery.data} creatorId={creatorId} />
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
    )
}

export default CreatorDossier
