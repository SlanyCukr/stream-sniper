'use client'

import Link from 'next/link'
import StatusChip from '@/components/common/StatusChip'
import { formatDate, formatTimeAgo } from '@/utils/dateUtils'
import HighlightedText from './HighlightedText'
import type { SearchHitVM } from './searchTypes'

interface SearchResultsListProps {
  hits: SearchHitVM[]
  query: string
  hasMore: boolean
  isFetchingMore: boolean
  isRefetching: boolean
  onLoadMore: () => void
  onOpenContext: (hit: SearchHitVM) => void
}

const SearchResultsList = ({
  hits, query, hasMore, isFetchingMore, isRefetching, onLoadMore, onOpenContext,
}: SearchResultsListProps) => (
  <>
    <div
      className={`pasta-list search-results${isRefetching ? ' is-refetching' : ''}`}
      aria-busy={isRefetching}
    >
      {hits.map(hit => (
        <article className="pasta-card search-result" key={hit.messageId}>
          <header className="search-result-head">
            <time className="mono search-result-time" dateTime={hit.time} title={formatDate(hit.time)}>
              {formatTimeAgo(hit.time)}
            </time>
            <span className="search-result-creator">{hit.creator.displayName}</span>
            <Link className="search-result-stream" href={`/stream/${hit.stream.id}`}>
              {hit.stream.title}
            </Link>
          </header>
          <p className="pasta-text search-result-text">
            <HighlightedText text={hit.text} query={query} />
          </p>
          <footer className="search-result-foot">
            <Link className="search-result-nick" href={`/chatter/${hit.chatter.id}`}>
              {hit.chatter.nick}
            </Link>
            {hit.chatter.isBot === true ? (
              <StatusChip variant="warn" aria-label={`${hit.chatter.nick} is flagged as a bot`}>
                BOT
              </StatusChip>
            ) : null}
            <button
              type="button"
              className="pasta-expand"
              onClick={() => onOpenContext(hit)}
            >
              Show in chat
            </button>
          </footer>
        </article>
      ))}
    </div>
    {hasMore ? (
      <div className="search-load-more">
        <button
          type="button"
          className="btn btn-outline-primary btn-sm"
          onClick={onLoadMore}
          disabled={isFetchingMore}
        >
          {isFetchingMore ? 'Loading…' : 'Load more'}
        </button>
      </div>
    ) : null}
  </>
)

export default SearchResultsList
