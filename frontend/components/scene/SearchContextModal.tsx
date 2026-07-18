'use client'

import { useEffect, useRef } from 'react'
import Link from 'next/link'
import { Modal } from 'react-bootstrap'
import QueryState from '@/components/common/QueryState'
import { useSearchContext } from '@/hooks/scene/useSearchQueries'
import HighlightedText from './HighlightedText'
import type { SearchContextVM } from './searchTypes'

interface SearchContextModalProps {
  streamId: number | null
  messageId: number | null
  query: string
  show: boolean
  onHide: () => void
}

const clockFromTs = (timestamp: string) => (String(timestamp).split('T')[1] || '').slice(0, 8)

const ContextBody = ({ data, query }: { data: SearchContextVM, query: string }) => {
  const hitRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    hitRef.current?.scrollIntoView({ block: 'center' })
  }, [data])

  return (
    <>
      <div className="search-context-meta mono text-muted">
        <span>{data.stream.creator.displayName}</span>
        <span aria-hidden="true"> · </span>
        <Link href={`/stream/${data.stream.id}`}>{data.stream.title}</Link>
      </div>
      <div className="origin-chat search-context-chat" role="log" aria-label="Chat context">
        {data.messages.map((message, index) => {
          const isHit = index === data.hitIndex
          return (
            <div
              key={message.id}
              ref={isHit ? hitRef : undefined}
              className={`origin-message${isHit ? ' is-pasta' : ''}`}
            >
              <span className="mono text-muted" aria-hidden="true">{clockFromTs(message.time)}</span>
              <span className="origin-nick">
                {message.isSubscriber ? <i className="bi bi-star-fill me-1" aria-hidden="true" title="Subscriber" /> : null}
                {message.nick}
              </span>
              <span className="search-context-text">
                {isHit
                  ? <HighlightedText text={message.text} query={query} />
                  : message.text}
              </span>
            </div>
          )
        })}
      </div>
    </>
  )
}

/** Chat-replay-style context window around a search hit, fetched on demand. */
const SearchContextModal = ({
  streamId, messageId, query, show, onHide,
}: SearchContextModalProps) => {
  const contextQuery = useSearchContext(
    { streamId, messageId },
    { enabled: show && Boolean(streamId) && Boolean(messageId) },
  )

  return (
    <Modal show={show} onHide={onHide} size="lg" centered scrollable>
      <Modal.Header closeButton>
        <Modal.Title>Message in context</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <QueryState
          query={contextQuery}
          errorTitle="Couldn't load the surrounding chat"
          loadingText="Loading chat context…"
          isEmpty={(value: SearchContextVM) => !value?.messages?.length}
          emptyTitle="No surrounding messages"
          showErrorDetails={false}
        >
          {(data: SearchContextVM) => <ContextBody data={data} query={query} />}
        </QueryState>
      </Modal.Body>
    </Modal>
  )
}

export default SearchContextModal
