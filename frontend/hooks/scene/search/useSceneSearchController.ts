import {
    useCallback, useEffect, useMemo, useState,
} from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { mapCreatorOption, useCreators, type CreatorOption } from '@/hooks/creator/useCreatorsQuery'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import type { SearchHitVM } from './searchTypes'
import {
    MIN_QUERY_LENGTH,
    useSearchFirst,
    useSearchFrequency,
    useSearchMessages,
} from './useSearchQueries'
import { buildSearchQueryString, readSearchState } from './searchUrlState'

const PAGE_SIZE = 50

/**
 * Controller for the scene chat-search surface, following the codebase's
 * controller-hook pattern for stateful views. Owns the whole "type in the
 * box → results render" flow: the editable input draft vs the committed URL
 * query (useSearchParams is the sole source of truth once committed), the
 * debounce → router.replace hand-off, the three search queries, infinite-page
 * flattening, and the context-modal selection. The view is a template.
 */
export const useSceneSearchController = () => {
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

    const isFetchingMore = messagesQuery.isFetchingNextPage

    return {
        committed,
        isSearchable,
        toolbarProps: {
            input,
            onInputChange: (value: string) => setInputDraft({ sourceQuery: urlState.q, value }),
            creators,
            selectedCreator,
            onCreatorChange: (option: CreatorOption | null) => replaceSearchState({
                q: committed,
                creatorId: option?.value ?? null,
                days,
            }),
            days,
            onDaysChange: (nextDays: number | null) => replaceSearchState({
                q: committed,
                creatorId,
                days: nextDays,
            }),
        },
        summary: {
            first: firstQuery.data,
            frequency: frequencyQuery.data,
        },
        results: {
            hits: accumulated,
            isError: messagesQuery.isError,
            error: messagesQuery.error,
            refetch: messagesQuery.refetch,
            isInitialLoading: (messagesQuery.isLoading || messagesQuery.isFetching) && accumulated.length === 0,
            hasMore: Boolean(messagesQuery.hasNextPage),
            isFetchingMore,
            isRefetching: messagesQuery.isFetching && !isFetchingMore && accumulated.length > 0,
            loadMore: () => void messagesQuery.fetchNextPage(),
        },
        contextModal: {
            hit: contextHit,
            open: setContextHit,
            close: () => setContextHit(null),
        },
    }
}
