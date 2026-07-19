import Image from 'next/image'
import Link from 'next/link'
import CardLinkButton from '@/components/common/CardLinkButton'
import type { CreatorSummary } from '@/hooks/creator/useCreatorSummaryQuery'
import { formatTimeAgo } from '@/utils/dateUtils'
import {
    formatCompactNumber, formatDurationHours,
} from '@/utils/numberUtils'

interface CreatorDossierOverviewProps {
    creator: CreatorSummary
    creatorId: number
}

const CreatorDossierOverview = ({ creator, creatorId }: CreatorDossierOverviewProps) => {
    const stats: Array<[string, string]> = [
        ['Streams', creator.totalStreams.toLocaleString()],
        ['Chat messages', formatCompactNumber(creator.totalMessages)],
        ['Hours captured', formatDurationHours(creator.durationSeconds)],
        ['Avg msgs/min', creator.messagesPerMinute == null ? '--' : creator.messagesPerMinute.toFixed(1)],
        ['Known audience', formatCompactNumber(creator.audienceSize)],
        ['Regulars', creator.regulars.toLocaleString()],
    ]
    return (
        <>
            <header className="page-header creator-dossier-header">
                <div className="creator-identity">
                    {creator.profileImageUrl ? (
                        <Image className="creator-avatar" src={creator.profileImageUrl} alt="" width={72} height={72} />
                    ) : null}
                    <div>
                        <p className="page-sub">
                            creator dossier · last seen {creator.lastStreamAt ? formatTimeAgo(creator.lastStreamAt) : 'never'}
                        </p>
                        <h1 className="page-title">{creator.displayName || creator.nick}</h1>
                        <p className="mono text-muted">@{creator.nick}</p>
                    </div>
                </div>
                <div className="d-flex gap-2">
                    <CardLinkButton
                        entity="creator"
                        id={creatorId}
                    />
                    <Link className="btn btn-outline-primary btn-sm" href={`/creator/${creatorId}/wrapped`}>
                        Wrapped
                    </Link>
                    <Link className="btn btn-outline-primary btn-sm" href={`/movement?creator=${creatorId}`}>
                        Audience movement
                    </Link>
                    {creator.latestStream ? (
                        <Link className="btn btn-outline-primary btn-sm" href={`/stream/${creator.latestStream.streamId}`}>
                            Latest stream
                        </Link>
                    ) : null}
                </div>
            </header>
            <div className="stats-strip" role="list" aria-label="Creator lifetime statistics">
                {stats.map(([label, value]) => (
                    <div className="stat-tile" role="listitem" key={label}>
                        <div className="stat-label">{label}</div>
                        <div className="stat-value">{value}</div>
                    </div>
                ))}
            </div>
        </>
    )
}

export default CreatorDossierOverview
