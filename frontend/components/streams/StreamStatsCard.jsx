'use client'
import {
    Card,
} from 'react-bootstrap'
import ChatterSmallInfo from '../ChatterSmallInfo'

/**
 * Stream Statistics Card Component
 */
const StreamStatsCard = ({
    mostActiveChatters, mostTaggedChatters, renderOtherCreators,
}) => (
    <Card>
        <Card.Body>
            <section aria-labelledby="most-active-heading">
                <h3 id="most-active-heading">Most active chatters</h3>
                <ul
                    role="list"
                    aria-label="Most active chatters in this stream">
                    {mostActiveChatters?.map(chatter => (
                        <ChatterSmallInfo
                            key={chatter[0]}
                            id={chatter[0]}
                            nick={chatter[1]}
                            count={chatter[2]}
                            noun="Count"
                        />
                    ))}
                </ul>
            </section>
            <section aria-labelledby="most-tagged-heading">
                <h3 id="most-tagged-heading">Most tagged chatters</h3>
                <ul
                    role="list"
                    aria-label="Most tagged chatters in this stream">
                    {mostTaggedChatters?.map(chatter => (
                        <ChatterSmallInfo
                            key={chatter[0]}
                            id={chatter[0]}
                            nick={chatter[1]}
                            count={chatter[2]}
                            noun="Tagged"
                        />
                    ))}
                </ul>
            </section>
            {renderOtherCreators}
        </Card.Body>
    </Card>
)

export default StreamStatsCard
