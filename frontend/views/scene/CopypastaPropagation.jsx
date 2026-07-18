'use client'

import Link from 'next/link'
import { Card } from 'react-bootstrap'
import { useCopypastaPropagation } from '@/hooks/scene/useSceneCopypastaQueries'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import { uiError } from '@/utils/errorUtils'
import QueryState from '@/components/common/QueryState'

const stamp = value => value ? value.replace('T', ' ').slice(0, 16) : '--'

const CopypastaPropagation = ({ messageTextId }) => {
    const query = useCopypastaPropagation(messageTextId)
    if (!Number.isInteger(messageTextId) || messageTextId <= 0) {
        return <ErrorAlert title="Invalid copypasta" error={uiError('This copypasta link is invalid. Go back and pick one from the library.')} />
    }

    return (
        <QueryState
            query={query}
            errorTitle="Failed to trace copypasta"
            loadingText="Tracing copypasta propagation..."
            showErrorDetails={false}
        >
            {pasta => (
                <>
                    <header className="page-head">
                        <div>
                            <p className="page-sub">meme propagation · first seen {stamp(pasta.firstSeen)}</p>
                            <h1 className="page-title">Copypasta trace</h1>
                        </div>
                        <Link className="btn btn-outline-primary btn-sm" href="/copypasta">Back to library</Link>
                    </header>

                    <Card className="pasta-origin-card">
                        <Card.Body>
                            <blockquote className="pasta-text mono">{pasta.text}</blockquote>
                            <div className="pasta-chips">
                                <span className="pasta-chip mono">{pasta.usageCount.toLocaleString()} uses</span>
                                <span className="pasta-chip mono">{pasta.creatorCount} channels</span>
                                <span className="pasta-chip mono">{pasta.streamCount} streams</span>
                                <span className="pasta-chip mono">{pasta.chatterAppearances} chatter appearances</span>
                            </div>
                        </Card.Body>
                    </Card>

                    <div className="propagation-grid">
                        <Card>
                            <Card.Body>
                                <div className="section-label">Propagation timeline</div>
                                <ol className="propagation-timeline">
                                    {pasta.occurrences.map((item, index) => (
                                        <li key={item.streamId}>
                                            <span className="propagation-node" aria-hidden="true" />
                                            <div>
                                                <div className="mono text-muted">{stamp(item.firstSeen)} {index === 0 ? '· origin' : ''}</div>
                                                <Link href={`/creator/${item.creatorId}`} className="propagation-creator">
                                                    {item.displayName || item.nick}
                                                </Link>
                                                <Link href={`/stream/${item.streamId}`} className="propagation-stream">
                                                    {item.streamTitle}
                                                </Link>
                                                <span className="mono text-muted">{item.usageCount} uses · {item.chatterCount} chatters</span>
                                            </div>
                                        </li>
                                    ))}
                                </ol>
                            </Card.Body>
                        </Card>

                        <Card>
                            <Card.Body>
                                <div className="section-label">Origin chat · ±90 seconds</div>
                                <div className="origin-chat" role="log">
                                    {pasta.originContext.map(message => (
                                        <div key={message.id} className={message.text === pasta.text ? 'origin-message is-pasta' : 'origin-message'}>
                                            <span className="mono text-muted">{message.time.slice(11, 19)}</span>
                                            <span className="origin-nick">{message.nick}</span>
                                            <span>{message.text}</span>
                                        </div>
                                    ))}
                                    {pasta.originContext.length === 0 ? <p className="text-muted">No surrounding chat available.</p> : null}
                                </div>
                            </Card.Body>
                        </Card>
                    </div>
                </>
            )}
        </QueryState>
    )
}

export default CopypastaPropagation
