'use client'

import Link from 'next/link'
import {
    RecapCopypastasSection,
    RecapEmotesSection,
    RecapMomentsSection,
    RecapTopChattersSection,
    RecapTotalsSection,
} from '@/components/wrapped/RecapSections'
import WrappedSection from '@/components/wrapped/WrappedSection'
import type { SceneWrapped } from '@/hooks/scene/useSceneWrappedQuery'
import { formatStreamTimestamp } from '@/utils/dateUtils'
import { formatCompactNumber, magnitudeBarWidth } from '@/utils/numberUtils'

const compactOrDash = (value: number | null): string => (
    value == null ? '—' : formatCompactNumber(value)
)

const WrappedRecap = ({ wrapped }: { wrapped: SceneWrapped }) => {
    const topCreatorMessages = wrapped.topCreators.reduce(
        (max, creator) => Math.max(max, creator.totalMessages),
        0,
    )

    return (
        <div className="wrapped-flow">
            <RecapTotalsSection totals={wrapped.totals} />

            {wrapped.topCreators.length > 0 ? (
                <WrappedSection label="Top creators">
                    <div className="card card-hud">
                        <div className="wrapped-table-scroll" role="region" aria-label="Top creators">
                            <table className="table wrapped-table mb-0">
                                <thead>
                                    <tr>
                                        <th scope="col">#</th>
                                        <th scope="col">Creator</th>
                                        <th scope="col" className="text-end">Messages</th>
                                        <th scope="col" className="text-end">Streams</th>
                                        <th scope="col" className="text-end">Peak</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {wrapped.topCreators.map(creator => (
                                        <tr key={creator.creatorId}>
                                            <td className="rank-num">
                                                {String(creator.rank).padStart(2, '0')}
                                            </td>
                                            <td>
                                                <Link
                                                    className="wrapped-creator"
                                                    href={`/creator/${creator.creatorId}`}
                                                >
                                                    {creator.profileImageUrl ? (
                                                        // eslint-disable-next-line @next/next/no-img-element
                                                        <img
                                                            className="scene-avatar"
                                                            src={creator.profileImageUrl}
                                                            alt=""
                                                            loading="lazy"
                                                        />
                                                    ) : (
                                                        <span
                                                            className="scene-avatar scene-avatar-empty"
                                                            aria-hidden="true"
                                                        />
                                                    )}
                                                    <span className="wrapped-creator-name">
                                                        {creator.displayName}
                                                    </span>
                                                </Link>
                                            </td>
                                            <td className="wrapped-messages text-end">
                                                <span className="mono">
                                                    {formatCompactNumber(creator.totalMessages)}
                                                </span>
                                                <span className="data-bar" aria-hidden="true">
                                                    <span
                                                        className="data-bar-fill"
                                                        style={{
                                                            width: `${magnitudeBarWidth(creator.totalMessages, topCreatorMessages)}%`,
                                                        }}
                                                    />
                                                </span>
                                            </td>
                                            <td className="mono text-end">
                                                {formatCompactNumber(creator.streams)}
                                            </td>
                                            <td className="mono text-end">
                                                {compactOrDash(creator.peakViewers)}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </WrappedSection>
            ) : null}

            <RecapTopChattersSection chatters={wrapped.topChatters} />
            <RecapMomentsSection moments={wrapped.topMoments} />
            <RecapCopypastasSection copypastas={wrapped.topCopypastas} />
            <RecapEmotesSection emotes={wrapped.topEmotes} />

            {wrapped.notableEvents.length > 0 ? (
                <WrappedSection label="Notable events">
                    <ul className="wrapped-timeline">
                        {wrapped.notableEvents.map((event, index) => (
                            <li
                                className="wrapped-event"
                                key={`${event.eventType}-${event.occurredAt}-${index}`}
                            >
                                <time className="wrapped-event-when mono" dateTime={event.occurredAt}>
                                    {formatStreamTimestamp(event.occurredAt)}
                                </time>
                                <div className="wrapped-event-body">
                                    <p className="wrapped-event-title">{event.title}</p>
                                    <p className="wrapped-event-summary">{event.summary}</p>
                                    {event.creatorDisplayName ? (
                                        <span className="wrapped-event-creator">
                                            {event.creatorDisplayName}
                                        </span>
                                    ) : null}
                                </div>
                            </li>
                        ))}
                    </ul>
                </WrappedSection>
            ) : null}
        </div>
    )
}

export default WrappedRecap
