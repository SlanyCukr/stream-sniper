'use client'

import EmptyState from '@/components/common/EmptyState'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import SearchToolbar from '@/components/scene/SearchToolbar'
import SearchResultsList from '@/components/scene/SearchResultsList'
import SearchFirstCard from '@/components/scene/SearchFirstCard'
import SearchFrequencySparkline from '@/components/scene/SearchFrequencySparkline'
import SearchContextModal from '@/components/scene/SearchContextModal'
import { MIN_QUERY_LENGTH } from '@/hooks/scene/search/useSearchQueries'
import { useSceneSearchController } from '@/hooks/scene/search/useSceneSearchController'

const SceneSearch = () => {
  const {
    committed, isSearchable, toolbarProps, summary, results, contextModal,
  } = useSceneSearchController()

  const renderResults = () => {
    if (results.isError && results.hits.length === 0) {
      return (
        <ErrorAlert
          error={results.error}
          title="Search failed"
          onRetry={results.refetch}
        />
      )
    }
    if (results.isInitialLoading) {
      return <LoadingSpinner text="Searching chat…" centered />
    }
    if (results.hits.length === 0) {
      return (
        <EmptyState title="No messages match this search">
          Try a different phrase, widen the time window, or clear the creator filter.
        </EmptyState>
      )
    }
    return (
      <SearchResultsList
        hits={results.hits}
        query={committed}
        hasMore={results.hasMore}
        isFetchingMore={results.isFetchingMore}
        isRefetching={results.isRefetching}
        onLoadMore={results.loadMore}
        onOpenContext={contextModal.open}
      />
    )
  }

  return (
    <>
      <header className="page-head">
        <div>
          <p className="page-sub">find any phrase across every captured chat</p>
          <h1 className="page-title">Search</h1>
        </div>
      </header>

      <SearchToolbar {...toolbarProps} />

      {!isSearchable ? (
        <EmptyState title="Search the scene's chat history">
          {`Type at least ${MIN_QUERY_LENGTH} characters to search across every captured stream.`}
        </EmptyState>
      ) : (
        <>
          <div className="row g-4 search-summary">
            <div className="col-12 col-lg-7">
              {summary.first ? (
                <SearchFirstCard data={summary.first} query={committed} />
              ) : null}
            </div>
            <div className="col-12 col-lg-5">
              {summary.frequency && summary.frequency.points.length > 0 ? (
                <div className="pasta-card search-frequency-card">
                  <h2 className="search-frequency-title">Mentions over time</h2>
                  <SearchFrequencySparkline points={summary.frequency.points} />
                </div>
              ) : null}
            </div>
          </div>
          {renderResults()}
        </>
      )}

      <SearchContextModal
        show={contextModal.hit !== null}
        onHide={contextModal.close}
        streamId={contextModal.hit?.stream.id ?? null}
        messageId={contextModal.hit?.messageId ?? null}
        query={committed}
      />
    </>
  )
}

export default SceneSearch
