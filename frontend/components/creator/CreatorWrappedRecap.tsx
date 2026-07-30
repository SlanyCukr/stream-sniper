'use client'

import {
    RecapCopypastasSection,
    RecapEmotesSection,
    RecapMomentsSection,
    RecapTopChattersSection,
    RecapTotalsSection,
} from '@/components/wrapped/RecapSections'
import type { CreatorWrapped } from '@/hooks/creator/useCreatorWrappedQuery'

const CreatorWrappedRecap = ({ wrapped }: { wrapped: CreatorWrapped }) => (
    <div className="wrapped-flow">
        <RecapTotalsSection totals={wrapped.totals} />
        <RecapTopChattersSection chatters={wrapped.topChatters} />
        <RecapMomentsSection moments={wrapped.topMoments} />
        <RecapCopypastasSection copypastas={wrapped.topCopypastas} />
        <RecapEmotesSection emotes={wrapped.topEmotes} />
    </div>
)

export default CreatorWrappedRecap
