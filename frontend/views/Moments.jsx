'use client'
import {
    useCallback,
    useMemo,
    useState,
} from 'react'
import Select from 'react-select'
import { keepPreviousData } from '@tanstack/react-query'
import {
    useCreators,
    useMomentReview,
    useMomentsQueue,
} from '@/hooks/useApiQuery'
import { useAuth } from '@/contexts/AuthContext'
import { PAGINATION } from '@/constants'
import MomentCard from '@/components/moments/MomentCard'
import PaginationComponent from '@/components/streams/PaginationComponent'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

const LIMIT = PAGINATION.ITEMS_PER_PAGE

// Status filter tabs. `value: undefined` => all statuses.
const STATUS_TABS = [
    {
        key: 'all',
        label: 'All',
        value: undefined,
    },
    {
        key: 'pending',
        label: 'Pending',
        value: 'pending',
    },
    {
        key: 'bookmarked',
        label: 'Bookmarked',
        value: 'bookmarked',
    },
    {
        key: 'rejected',
        label: 'Rejected',
        value: 'rejected',
    },
    {
        key: 'clipped',
        label: 'Clipped',
        value: 'clipped',
    },
    {
        key: 'published',
        label: 'Published',
        value: 'published',
    },
]

const EMPTY_HINT = {
    all: 'No chat spikes have been enriched yet. Run the rollup backfill to populate the queue.',
    pending: 'Nothing awaiting review — every surfaced moment has been triaged.',
    bookmarked: 'No bookmarked moments yet. Bookmark spikes worth clipping to collect them here.',
    rejected: 'No rejected moments.',
    clipped: 'No clips attached yet.',
    published: 'No published highlights yet.',
}

/**
 * Highlight queue: reviewable chat-spike moments across all tracked creators.
 * Filterable by review status and creator, paginated against the queue total.
 * Review actions (bookmark / reject / clear) are admin-only and mutate the
 * shared curation state. On refetch the previous page is held at reduced
 * opacity (keepPreviousData) rather than flashing a skeleton.
 */
const Moments = () => {
    const { isAdmin } = useAuth()

    const [
        statusKey,
        setStatusKey,
    ] = useState('all')
    const [
        selectedCreator,
        setSelectedCreator,
    ] = useState(null)
    const [
        page,
        setPage,
    ] = useState(0)

    const status = useMemo(
        () => STATUS_TABS.find(tab => tab.key === statusKey)?.value,
        [
            statusKey,
        ],
    )
    const creatorId = selectedCreator?.value || undefined

    const {
        data: creatorsData,
        error: creatorsError,
        refetch: refetchCreators,
    } = useCreators()

    const creators = useMemo(() => creatorsData?.map(creator => ({
        label: creator[1],
        value: creator[0],
    })) || [
    ], [
        creatorsData,
    ])

    const {
        data,
        isLoading,
        isPlaceholderData,
        error,
        refetch,
    } = useMomentsQueue(
        {
            status,
            creatorId,
            limit: LIMIT,
            offset: page * LIMIT,
        },
        { placeholderData: keepPreviousData },
    )

    const review = useMomentReview()

    const handleStatusChange = useCallback(key => {
        setStatusKey(key)
        setPage(0)
    }, [
    ])

    const handleCreatorChange = useCallback(option => {
        setSelectedCreator(option)
        setPage(0)
    }, [
    ])

    const handleReview = useCallback((moment, nextStatus, metadata = {}) => {
        review.mutate({
            streamId: moment.streamId,
            bucketMinute: moment.t,
            status: nextStatus,
            clipUrl: metadata.clipUrl,
            note: metadata.note,
        })
    }, [
        review,
    ])

    const items = data?.items || [
    ]
    const total = data?.total || 0
    const pagesCount = Math.ceil(total / LIMIT)

    // Identify the row whose review mutation is currently in flight so only that
    // card's buttons disable (last-writer-wins, one mutation at a time).
    const pendingKey = review.isPending && review.variables
        ? `${review.variables.streamId}:${review.variables.bucketMinute}`
        : null

    return (
        <>
            <div className="page-head">
                <div>
                    <p className="page-sub">chat spikes worth clipping</p>
                    <h1 className="page-title">Highlights</h1>
                </div>
            </div>

            {creatorsError && (
                <ErrorAlert
                    error={creatorsError}
                    title="Failed to load creators"
                    onRetry={refetchCreators}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            )}

            <div
                className="toolbar moment-toolbar"
                role="search"
                aria-label="Highlight queue filters">
                <div
                    className="chatter-tabs"
                    role="tablist"
                    aria-label="Review status">
                    {STATUS_TABS.map(tab => (
                        <button
                            key={tab.key}
                            type="button"
                            role="tab"
                            id={`moment-tab-${tab.key}`}
                            aria-selected={statusKey === tab.key}
                            className={statusKey === tab.key ? 'chatter-tab active' : 'chatter-tab'}
                            onClick={() => handleStatusChange(tab.key)}>
                            {tab.label}
                        </button>
                    ))}
                </div>

                <div className="toolbar-field moment-creator-field">
                    <label
                        htmlFor="moment-creator-select"
                        className="visually-hidden">
                        Filter by creator
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="moment-creator-select"
                        inputId="moment-creator-select"
                        options={creators}
                        value={selectedCreator}
                        onChange={handleCreatorChange}
                        placeholder="All creators..."
                        isClearable
                        aria-label="Filter by creator"
                    />
                </div>
            </div>

            {error ? (
                <ErrorAlert
                    error={error}
                    title="Failed to load highlight queue"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : isLoading ? (
                <LoadingSpinner
                    text="Loading highlight queue..."
                    centered
                />
            ) : items.length === 0 ? (
                <div className="empty-state">
                    <span
                        className="empty-scope"
                        aria-hidden="true"></span>
                    <p className="empty-title">No moments</p>
                    <p className="empty-hint">{EMPTY_HINT[statusKey]}</p>
                </div>
            ) : (
                <>
                    <div
                        className={`moment-queue${isPlaceholderData ? ' is-refetching' : ''}`}
                        aria-busy={isPlaceholderData}>
                        {items.map(moment => {
                            const key = `${moment.streamId}:${moment.t}`
                            return (
                                <MomentCard
                                    key={key}
                                    moment={moment}
                                    isAdmin={isAdmin}
                                    pending={pendingKey === key}
                                    onReview={(next, metadata) => handleReview(moment, next, metadata)}
                                />
                            )
                        })}
                    </div>

                    <PaginationComponent
                        pagesCount={pagesCount}
                        offset={page}
                        updateOffset={setPage}
                    />
                </>
            )}
        </>
    )
}

export default Moments
