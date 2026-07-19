'use client'
import type { ReactNode } from 'react'
import LoadingSpinner, { type LoadingSize } from '@/components/common/LoadingSpinner'
import ErrorAlert, { type DetailedError } from '@/components/common/error/ErrorAlert'
import EmptyState from '@/components/common/EmptyState'

/**
 * Owns the loading / error / empty / content decision for a React Query result so
 * views stop hand-rolling (and subtly diverging on) that branching.
 *
 * Policy (single source of truth for every view). Let "empty" mean no data yet OR
 * a resolved payload the `isEmpty` predicate rejects:
 *   1. error present AND result is empty  → <ErrorAlert> (retry wired to refetch)
 *   2. still loading with no data yet      → <LoadingSpinner>
 *   3. result empty, no error              → empty slot (emptyState node or title/hint)
 *   4. otherwise (real, non-empty data)    → children(data)
 *
 * Stale data wins over a transient refetch error ONLY when there is real content
 * to protect: a background refetch failure never blanks out already-rendered
 * non-empty data (case 4). But when the last success was empty there is nothing
 * worth preserving, so an error surfaces as an <ErrorAlert> with retry (case 1)
 * rather than an indistinguishable-from-quiet empty placeholder.
 *
 * Render-prop `children` receives the resolved (non-null) data, so call sites
 * never re-null-check. Works both as a whole-view gate (return <QueryState>…) and
 * as a data-section slot inside persistent page chrome.
 */

/** The React Query result object. */
interface QueryStateQuery<TData> {
    data?: TData
    error?: unknown
    isLoading?: boolean
    isPending?: boolean
    refetch?: () => unknown
}

interface QueryStateProps<TData> {
    query: QueryStateQuery<TData>
    /** Title for the ErrorAlert. */
    errorTitle?: string
    /** Text for the LoadingSpinner. */
    loadingText?: string
    loadingSize?: LoadingSize
    /** Render the spinner inside a card. */
    loadingCard?: boolean
    /** Predicate deciding the empty slot; defaults to never-empty. */
    isEmpty?: (data: TData) => boolean
    /** Custom empty node; overrides emptyTitle/emptyHint. */
    emptyState?: ReactNode
    /** Shorthand empty-state title (used when emptyState is absent). */
    emptyTitle?: string
    emptyHint?: ReactNode
    /** Retry handler; defaults to query.refetch. */
    onRetry?: (() => unknown) | null
    /** Show the ErrorAlert details toggle; defaults to dev only. */
    showErrorDetails?: boolean
    /** Render prop for resolved data. */
    children: (data: TData) => ReactNode
}

const QueryState = <TData,>({
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
}: QueryStateProps<TData>) => {
    const data = query?.data
    const error = query?.error
    // RQ v5 exposes both; isLoading == isPending && isFetching (no data yet).
    const isLoading = query?.isLoading ?? query?.isPending ?? false
    const hasData = data !== undefined && data !== null
    const isEmptyResult = !hasData || (isEmpty ? isEmpty(data) : false)
    const retry = onRetry === undefined ? query?.refetch : onRetry
    const detailsVisible = showErrorDetails === undefined
        ? process.env.NODE_ENV === 'development'
        : showErrorDetails

    const emptySlot = () => (emptyState !== undefined
        ? emptyState
        : <EmptyState title={emptyTitle}>{emptyHint}</EmptyState>)

    // Error wins whenever there is no real content to protect (no data, or a
    // resolved-but-empty payload). Real non-empty data survives a transient
    // refetch error and falls through to children() below.
    if (error && isEmptyResult) {
        return (
            <ErrorAlert
                // Query errors are caller-defined (Axios, native, etc.); narrowing
                // happens inside normalizeApiError, so this boundary cast is safe.
                error={error as DetailedError}
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

    if (isEmptyResult) {
        return emptySlot()
    }

    // hasData/isEmptyResult are runtime checks, not type guards, so TS still
    // sees `data` as possibly undefined here even though we know it isn't.
    return children(data as TData)
}

export default QueryState
