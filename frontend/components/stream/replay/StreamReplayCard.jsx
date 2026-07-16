// @ts-check
'use client'
import { Card } from 'react-bootstrap'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import StreamChatReplay from './StreamChatReplay'
import StreamReplayFilters from './StreamReplayFilters'

/**
 * Stream chat replay coordinator. The parent owns server-side query state;
 * StreamReplayFilters owns filter drafts and StreamChatReplay owns the
 * virtualized message list.
 * @param {object} props
 * @param {{label:string, value:number}[]} props.chatterOptions
 * @param {object} props.replay
 * @param {{onChatterChange:(chatterId:number|undefined)=>void, onQueryChange:(query:string|undefined)=>void, onSubOnlyChange:(subOnly:boolean)=>void}} props.replay.filterCommands
 * @param {{messages:{id:number, ts:string, chatterId:number, nick:string, text:string, isSubscriber:boolean, badges:unknown}[], hasMore:boolean, isFetchingMore:boolean, onLoadMore:()=>void|Promise<unknown>}} props.replay.messagePage
 * @param {{isLoading:boolean, error:Error|null}} props.replay.queryState
 * @param {{jumpToTs:{ts:string, nonce:number}|null}} props.replay.navigation
 */
const StreamReplayCard = ({
    chatterOptions,
    replay,
}) => {
    const { filterCommands, messagePage, queryState, navigation } = replay
    return (
        <Card>
            <Card.Body>
                <h2 className="section-label mb-1" id="chat-replay-heading">Chat replay</h2>
                <p className="text-muted small mb-3">
                    {chatterOptions.length.toLocaleString()} chatters recorded — filter by chatter or search the text.
                </p>

                <StreamReplayFilters
                    chatterOptions={chatterOptions}
                    onChatterChange={filterCommands.onChatterChange}
                    onQueryChange={filterCommands.onQueryChange}
                    onSubOnlyChange={filterCommands.onSubOnlyChange}
                />

                {queryState.error ? (
                    <ErrorAlert error={queryState.error} title="Failed to load messages" className="mt-3" />
                ) : null}
                {queryState.isLoading && !queryState.error ? (
                    <LoadingSpinner text="Loading messages..." className="mt-3" />
                ) : !queryState.error ? (
                    <StreamChatReplay
                        messages={messagePage.messages}
                        hasMore={messagePage.hasMore}
                        isFetchingMore={messagePage.isFetchingMore}
                        onLoadMore={messagePage.onLoadMore}
                        jumpToTs={navigation.jumpToTs}
                    />
                ) : null}
            </Card.Body>
        </Card>
    )
}

export default StreamReplayCard
