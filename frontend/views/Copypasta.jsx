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
    useSceneCopypastas,
} from '@/hooks/useApiQuery'
import CopypastaCard from '@/components/scene/CopypastaCard'
import PaginationComponent from '@/components/streams/PaginationComponent'
import LoadingSpinner from '@/components/LoadingSpinner'
import ErrorAlert from '@/components/ErrorAlert'

// Copypasta pages are their own size (independent of the stream-grid page size).
const LIMIT = 25

const SORT_OPTIONS = [
    {
        value: 'usage',
        label: 'Most used',
    },
    {
        value: 'spread',
        label: 'Widest spread',
    },
    {
        value: 'recent',
        label: 'Recent',
    },
]

/**
 * Copypasta library: the most-repeated chat lines across all captured streams,
 * filterable by creator and sortable by usage / spread / recency. Offset
 * paginated against the total. On refetch the previous page is held at reduced
 * opacity (keepPreviousData) rather than flashing a skeleton.
 */
const Copypasta = () => {
    const [
        selectedCreator,
        setSelectedCreator,
    ] = useState(null)
    const [
        selectedSort,
        setSelectedSort,
    ] = useState(SORT_OPTIONS[0])
    const [
        page,
        setPage,
    ] = useState(0)

    const creatorId = selectedCreator?.value || undefined
    const sort = selectedSort?.value || 'usage'

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
    } = useSceneCopypastas(
        {
            creatorId,
            sort,
            limit: LIMIT,
            offset: page * LIMIT,
        },
        { placeholderData: keepPreviousData },
    )

    const handleCreatorChange = useCallback(option => {
        setSelectedCreator(option)
        setPage(0)
    }, [
    ])

    const handleSortChange = useCallback(option => {
        setSelectedSort(option || SORT_OPTIONS[0])
        setPage(0)
    }, [
    ])

    const items = data?.items || [
    ]
    const total = data?.total || 0
    const pagesCount = Math.ceil(total / LIMIT)

    return (
        <>
            <div className="page-head">
                <div>
                    <h1 className="page-title">Copypasta</h1>
                    <p className="page-sub">The scene&apos;s most-repeated chat lines</p>
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
                className="toolbar copypasta-toolbar"
                role="search"
                aria-label="Copypasta filters">
                <div className="toolbar-field copypasta-creator-field">
                    <label
                        htmlFor="copypasta-creator-select"
                        className="visually-hidden">
                        Filter by creator
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="copypasta-creator-select"
                        inputId="copypasta-creator-select"
                        options={creators}
                        value={selectedCreator}
                        onChange={handleCreatorChange}
                        placeholder="All creators..."
                        isClearable
                        aria-label="Filter by creator"
                    />
                </div>
                <div className="toolbar-field copypasta-sort-field">
                    <label
                        htmlFor="copypasta-sort-select"
                        className="visually-hidden">
                        Sort order
                    </label>
                    <Select
                        classNamePrefix="rs"
                        instanceId="copypasta-sort-select"
                        inputId="copypasta-sort-select"
                        options={SORT_OPTIONS}
                        value={selectedSort}
                        onChange={handleSortChange}
                        isSearchable={false}
                        aria-label="Sort order"
                    />
                </div>
            </div>

            {error ? (
                <ErrorAlert
                    error={error}
                    title="Failed to load copypasta library"
                    onRetry={refetch}
                    showDetails={process.env.NODE_ENV === 'development'}
                />
            ) : isLoading ? (
                <LoadingSpinner
                    text="Loading copypasta..."
                    centered
                />
            ) : items.length === 0 ? (
                <div className="empty-state">
                    <span
                        className="empty-scope"
                        aria-hidden="true" />
                    <p className="empty-title">No copypasta yet</p>
                    <p className="empty-hint">
                        Nothing has been rolled up for this filter yet. Run
                        {' '}
                        <span className="mono">stream-sniper-rollup --all --force</span>
                        {' '}
                        to populate the library.
                    </p>
                </div>
            ) : (
                <>
                    <div
                        className={`pasta-list${isPlaceholderData ? ' is-refetching' : ''}`}
                        aria-busy={isPlaceholderData}>
                        {items.map(pasta => (
                            <CopypastaCard
                                key={pasta.messageTextId}
                                pasta={pasta}
                            />
                        ))}
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

export default Copypasta
