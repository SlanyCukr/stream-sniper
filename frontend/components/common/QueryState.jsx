'use client'
import React from 'react'
import LoadingSpinner from '@/components/common/LoadingSpinner'
import ErrorAlert from '@/components/common/error/ErrorAlert'
import EmptyState from '@/components/common/EmptyState'

/**
 * Owns the loading / error / empty / content decision for a React Query result so
 * views stop hand-rolling (and subtly diverging on) that branching.
 *
 * Policy (single source of truth for every view):
 *   1. error present AND no usable data  → <ErrorAlert> (retry wired to refetch)
 *   2. still loading with no data yet     → <LoadingSpinner>
 *   3. data resolved but empty            → empty slot (emptyState node or title/hint)
 *   4. otherwise                          → children(data)
 *
 * Stale data wins over a transient refetch error (case 1 requires "no usable
 * data"), so a background refetch failure never blanks out already-rendered
 * content — the view keeps showing the last good data.
 *
 * Render-prop `children` receives the resolved (non-null) data, so call sites
 * never re-null-check. Works both as a whole-view gate (return <QueryState>…) and
 * as a data-section slot inside persistent page chrome.
 *
 * @typedef {object} QueryStateProps
 * @property {{data?:any, error?:any, isLoading?:boolean, isPending?:boolean, refetch?:()=>unknown}} query
 *   The React Query result object.
 * @property {string} [errorTitle]   Title for the ErrorAlert.
 * @property {string} [loadingText]  Text for the LoadingSpinner.
 * @property {import('./LoadingSpinner').LoadingSize} [loadingSize]
 * @property {boolean} [loadingCard] Render the spinner inside a card.
 * @property {(data:any)=>boolean} [isEmpty] Predicate deciding the empty slot; defaults to never-empty.
 * @property {React.ReactNode} [emptyState] Custom empty node; overrides emptyTitle/emptyHint.
 * @property {string} [emptyTitle]  Shorthand empty-state title (used when emptyState is absent).
 * @property {React.ReactNode} [emptyHint] Shorthand empty-state hint.
 * @property {(()=>unknown)|null} [onRetry] Retry handler; defaults to query.refetch.
 * @property {boolean} [showErrorDetails] Show the ErrorAlert details toggle; defaults to dev only.
 * @property {(data:any)=>React.ReactNode} children Render prop for resolved data.
 */

/** @param {QueryStateProps} props */
const QueryState = ({
    query,
    errorTitle = 'Something went wrong',
    loadingText = 'Loading…',
    loadingSize = 'lg',
    loadingCard = false,
    isEmpty = undefined,
    emptyState = undefined,
    emptyTitle = 'Nothing here yet',
    emptyHint = undefined,
    onRetry = undefined,
    showErrorDetails = undefined,
    children,
}) => {
    const data = query?.data
    const error = query?.error
    // RQ v5 exposes both; isLoading == isPending && isFetching (no data yet).
    const isLoading = query?.isLoading ?? query?.isPending ?? false
    const hasData = data !== undefined && data !== null
    const retry = onRetry === undefined ? query?.refetch : onRetry
    const detailsVisible = showErrorDetails === undefined
        ? process.env.NODE_ENV === 'development'
        : showErrorDetails

    if (error && !hasData) {
        return (
            <ErrorAlert
                error={error}
                title={errorTitle}
                onRetry={retry || undefined}
                showDetails={detailsVisible}
            />
        )
    }

    if (isLoading && !hasData) {
        return (
            <LoadingSpinner
                size={loadingSize}
                text={loadingText}
                card={loadingCard}
            />
        )
    }

    if (!hasData) {
        // No data, not loading, no error (e.g. query disabled / idle) — treat as empty.
        return emptyState !== undefined
            ? emptyState
            : <EmptyState title={emptyTitle}>{emptyHint}</EmptyState>
    }

    if (isEmpty && isEmpty(data)) {
        return emptyState !== undefined
            ? emptyState
            : <EmptyState title={emptyTitle}>{emptyHint}</EmptyState>
    }

    return children(data)
}

export default React.memo(QueryState)
