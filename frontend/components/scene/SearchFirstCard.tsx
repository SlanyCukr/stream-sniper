'use client'

import Link from 'next/link'
import { Card } from 'react-bootstrap'
import { formatDate, formatTimeAgo } from '@/utils/dateUtils'
import HighlightedText from './HighlightedText'
import type { SearchFirstVM, SearchHitVM } from './searchTypes'

interface SearchFirstCardProps {
  data: SearchFirstVM
  query: string
}

const HitLine = ({ hit, query, rank }: { hit: SearchHitVM, query: string, rank?: string }) => (
  <div className="search-first-hit">
    {rank ? <span className="search-first-rank mono">{rank}</span> : null}
    <div className="search-first-hit-body">
      <div className="mono text-muted search-first-meta">
        <span className="search-first-creator">{hit.creator.displayName}</span>
        <span aria-hidden="true"> · </span>
        <Link href={`/chatter/${hit.chatter.id}`}>{hit.chatter.nick}</Link>
        <span aria-hidden="true"> · </span>
        <time dateTime={hit.time} title={formatDate(hit.time)}>{formatTimeAgo(hit.time)}</time>
      </div>
      <p className="pasta-text search-first-text">
        <HighlightedText text={hit.text} query={query} />
      </p>
      <Link className="search-first-stream" href={`/stream/${hit.stream.id}`}>
        {hit.stream.title}
      </Link>
    </div>
  </div>
)

/** "Who said it first" — the earliest hit across the scene plus the earliest
 * hit per creator, with the total match count. */
const SearchFirstCard = ({ data, query }: SearchFirstCardProps) => (
  <Card className="search-first-card">
    <Card.Body>
      <div className="search-first-head">
        <h2 className="search-first-title">Who said it first</h2>
        <span className="search-first-total mono">
          {data.totalMatches.toLocaleString()}
          <span className="search-first-total-unit"> matches</span>
        </span>
      </div>
      {/* The origin is deliberately all-time: it ignores the page's time-window
          filter, which only scopes the results list and sparkline below. */}
      <p className="text-muted mono search-first-scope-note">
        all-time · ignores the time window filter
      </p>
      {data.first ? (
        <HitLine hit={data.first} query={query} rank="1st" />
      ) : (
        <p className="text-muted mb-0">No matches for this query yet.</p>
      )}
      {data.byCreator.length > 0 ? (
        <>
          <h3 className="search-first-subtitle">Earliest per creator</h3>
          <div className="search-first-list">
            {data.byCreator.map(hit => (
              <HitLine key={`${hit.creator.id}-${hit.messageId}`} hit={hit} query={query} />
            ))}
          </div>
        </>
      ) : null}
    </Card.Body>
  </Card>
)

export default SearchFirstCard
