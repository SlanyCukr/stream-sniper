import {
    useCallback, useMemo, useRef, useState,
} from 'react'
import { toUiFailure } from '@/utils/errorUtils'
import { useStreamMessages } from './useStreamMessagesQuery'

const reachesTimestamp = (pages, targetTs) => pages.some(
    page => page.messages.some(message => message.ts >= targetTs),
)

const REPLAY_JUMP_PAGE_BUDGET = 10
const REPLAY_JUMP_TIME_BUDGET_MS = 5000

/** @typedef {{pages: {messages: {ts:string}[]}[]}} ReplayData */

/**
 * Load a bounded number of replay pages while looking for a timeline target.
 * A later invocation can continue from pages cached by the query client.
 * @param {object} options
 * @param {ReplayData|undefined} options.initialData
 * @param {string} options.targetTs
 * @param {boolean|undefined} options.hasNextPage
 * @param {() => Promise<{data?: ReplayData, hasNextPage?: boolean}>} options.fetchNextPage
 * @param {number} [options.maxPages]
 * @param {number} [options.maxElapsedMs]
 * @param {() => number} [options.now]
 * @returns {Promise<{status:'found'|'exhausted'|'unavailable', data:ReplayData|undefined, pagesFetched:number}>}
 */
export const loadUntilTimestamp = async ({
    initialData,
    targetTs,
    hasNextPage,
    fetchNextPage,
    maxPages = REPLAY_JUMP_PAGE_BUDGET,
    maxElapsedMs = REPLAY_JUMP_TIME_BUDGET_MS,
    now = Date.now,
}) => {
    if (initialData && reachesTimestamp(initialData.pages, targetTs)) {
        return { status: 'found', data: initialData, pagesFetched: 0 }
    }
    if (!initialData || !hasNextPage) {
        return { status: 'unavailable', data: initialData, pagesFetched: 0 }
    }

    const startedAt = now()
    let current = initialData
    let canFetch = hasNextPage
    let pagesFetched = 0

    while (
        canFetch
        && pagesFetched < maxPages
        && now() - startedAt < maxElapsedMs
    ) {
        const result = await fetchNextPage()
        current = result.data
        canFetch = Boolean(result.hasNextPage)
        pagesFetched += 1

        if (current && reachesTimestamp(current.pages, targetTs)) {
            return { status: 'found', data: current, pagesFetched }
        }
    }

    return {
        status: canFetch ? 'exhausted' : 'unavailable',
        data: current,
        pagesFetched,
    }
}

export const useStreamReplayController = streamId => {
    const [chatterId, setChatterId] = useState(undefined)
    const [textQuery, setTextQuery] = useState(undefined)
    const [subOnly, setSubOnly] = useState(false)
    const [jumpToTs, setJumpToTs] = useState(null)
    const [jumpFailure, setJumpFailure] = useState(
        /** @type {ReturnType<typeof toUiFailure>|null} */ (null),
    )
    const jumpingRef = useRef(false)

    const messagesQuery = useStreamMessages(streamId, {
        chatterId,
        q: textQuery,
        subOnly,
    })
    const {
        data,
        fetchNextPage,
        hasNextPage,
        isFetchingNextPage,
    } = messagesQuery

    const messages = useMemo(
        () => data?.pages.flatMap(page => page.messages) ?? [],
        [data],
    )

    const handleLoadMore = useCallback(() => {
        if (hasNextPage && !isFetchingNextPage) fetchNextPage()
    }, [hasNextPage, isFetchingNextPage, fetchNextPage])

    const handleJump = useCallback(async targetTs => {
        if (!targetTs || jumpingRef.current) return

        jumpingRef.current = true
        setJumpFailure(null)
        try {
            const outcome = await loadUntilTimestamp({
                initialData: data,
                targetTs,
                hasNextPage,
                fetchNextPage,
            })
            if (outcome.status === 'found') {
                setJumpToTs({ ts: targetTs, nonce: Date.now() })
            } else {
                const message = outcome.status === 'exhausted'
                    ? 'That point is further back than the chat loaded so far. Select it again to keep loading.'
                    : "That point isn't in the recorded chat history."
                setJumpFailure(toUiFailure(new Error(message), message))
            }
        } catch (jumpError) {
            setJumpFailure(toUiFailure(jumpError, 'Failed to load replay target'))
        } finally {
            jumpingRef.current = false
        }
    }, [data, hasNextPage, fetchNextPage])

    return {
        filterCommands: {
            onChatterChange: setChatterId,
            onQueryChange: setTextQuery,
            onSubOnlyChange: setSubOnly,
        },
        messagePage: {
            messages,
            hasMore: Boolean(hasNextPage),
            isFetchingMore: isFetchingNextPage,
            onLoadMore: handleLoadMore,
        },
        queryState: {
            error: messagesQuery.error,
            isLoading: messagesQuery.isLoading,
        },
        navigation: {
            jumpToTs,
            jumpFailure,
            onJump: handleJump,
        },
    }
}
