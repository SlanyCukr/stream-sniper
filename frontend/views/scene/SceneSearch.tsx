'use client'

import {
  useCallback, useEffect, useMemo, useState,
} from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import EmptyState from '@/components/common/EmptyState'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import SearchToolbar from '@/components/scene/SearchToolbar'
import SearchResultsList from '@/components/scene/SearchResultsList'
import SearchFirstCard from '@/components/scene/SearchFirstCard'
import SearchFrequencySparkline from '@/components/scene/SearchFrequencySparkline'
import SearchContextModal from '@/components/scene/SearchContextModal'
import type { SearchHitVM } from '@/hooks/scene/search/searchTypes'
import { mapCreatorOption, useCreators } from '@/hooks/creator/useCreatorsQuery'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import {
  MIN_QUERY_LENGTH,
  useSearchFirst,
  useSearchFrequency,
  useSearchMessages,
} from '@/hooks/scene/search/useSearchQueries'
import { buildSearchQueryString, readSearchState } from '@/hooks/scene/search/searchUrlState'

const PAGE_SIZE = 50

const SceneSearch = () => {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const urlState = useMemo(() => readSearchState(searchParams), [searchParams])
  const { creatorId, days } = urlState
  const [inputDraft, setInputDraft] = useState({
    sourceQuery: urlState.q,
    value: urlState.q,
  })
  const input = inputDraft.sourceQuery === urlState.q ? inputDraft.value : urlState.q

  const debouncedInput = useDebouncedValue(input, 400)
  const committed = urlState.q.trim()
  const isSearchable = committed.length >= MIN_QUERY_LENGTH

  const replaceSearchState = useCallback((nextState: {
    q: string
    creatorId: number | null
    days: number | null
  }) => {
    const qs = buildSearchQueryString(nextState)
    if (qs === searchParams.toString()) return
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }, [pathname, router, searchParams])

  // The input is an editable draft; its debounced value becomes committed by
  // navigating, after which useSearchParams is the sole result/filter source.
  useEffect(() => {
    if (debouncedInput.trim() === committed) return
    replaceSearchState({ q: debouncedInput, creatorId, days })
  }, [committed, creatorId, days, debouncedInput, replaceSearchState])

  const creatorsQuery = useCreators()
  const creators = useMemo(
    () => creatorsQuery.data?.map(mapCreatorOption) ?? [],
    [creatorsQuery.data],
  )
  const selectedCreator = useMemo(
    () => creators.find(option => option.value === creatorId) ?? null,
    [creators, creatorId],
  )

  const messagesQuery = useSearchMessages({
    q: committed, creatorId, days, limit: PAGE_SIZE,
  })
  const firstQuery = useSearchFirst({ q: committed, creatorId })
  const frequencyQuery = useSearchFrequency({ q: committed, days: days ?? 90, creatorId })

  const accumulated = useMemo(
    () => messagesQuery.data?.pages.flatMap(page => page.items) ?? [],
    [messagesQuery.data],
  )

  const [contextHit, setContextHit] = useState<SearchHitVM | null>(null)

  const hasMore = Boolean(messagesQuery.hasNextPage)
  const isFetchingMore = messagesQuery.isFetchingNextPage
  const isRefetching = messagesQuery.isFetching && !isFetchingMore && accumulated.length > 0

  const renderResults = () => {
    if (messagesQuery.isError && accumulated.length === 0) {
      return (
        <ErrorAlert
          error={messagesQuery.error}
          title="Search failed"
          onRetry={messagesQuery.refetch}
        />
      )
    }
    if ((messagesQuery.isLoading || messagesQuery.isFetching) && accumulated.length === 0) {
      return <LoadingSpinner text="Searching chat…" centered />
    }
    if (accumulated.length === 0) {
      return (
        <EmptyState title="No messages match this search">
          Try a different phrase, widen the time window, or clear the creator filter.
        </EmptyState>
      )
    }
    return (
      <SearchResultsList
        hits={accumulated}
        query={committed}
        hasMore={hasMore}
        isFetchingMore={isFetchingMore}
        isRefetching={isRefetching}
        onLoadMore={() => void messagesQuery.fetchNextPage()}
        onOpenContext={setContextHit}
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

      <SearchToolbar
        input={input}
        onInputChange={value => setInputDraft({ sourceQuery: urlState.q, value })}
        creators={creators}
        selectedCreator={selectedCreator}
        onCreatorChange={option => replaceSearchState({
          q: committed,
          creatorId: option?.value ?? null,
          days,
        })}
        days={days}
        onDaysChange={nextDays => replaceSearchState({
          q: committed,
          creatorId,
          days: nextDays,
        })}
      />

      {!isSearchable ? (
        <EmptyState title="Search the scene's chat history">
          {`Type at least ${MIN_QUERY_LENGTH} characters to search across every captured stream.`}
        </EmptyState>
      ) : (
        <>
          <div className="row g-4 search-summary">
            <div className="col-12 col-lg-7">
              {firstQuery.data ? (
                <SearchFirstCard data={firstQuery.data} query={committed} />
              ) : null}
            </div>
            <div className="col-12 col-lg-5">
              {frequencyQuery.data && frequencyQuery.data.points.length > 0 ? (
                <div className="pasta-card search-frequency-card">
                  <h2 className="search-frequency-title">Mentions over time</h2>
                  <SearchFrequencySparkline points={frequencyQuery.data.points} />
                </div>
              ) : null}
            </div>
          </div>
          {renderResults()}
        </>
      )}

      <SearchContextModal
        show={contextHit !== null}
        onHide={() => setContextHit(null)}
        streamId={contextHit?.stream.id ?? null}
        messageId={contextHit?.messageId ?? null}
        query={committed}
      />
    </>
  )
}

export default SceneSearch
