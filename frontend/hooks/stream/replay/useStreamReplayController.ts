import {
    useCallback, useMemo, useRef, useState,
} from 'react'
import { toUiFailure, type UiFailure } from '@/utils/errorUtils'
import { useStreamMessages, type StreamMessagesPage } from './useStreamMessagesQuery'
import type { JumpTarget } from './useChatReplayNavigation'

interface ReplayData {
    pages: { messages: { ts: string }[] }[]
}

const reachesTimestamp = (pages: ReplayData['pages'], targetTs: string): boolean => pages.some(
    page => page.messages.some(message => message.ts >= targetTs),
)

const REPLAY_JUMP_PAGE_BUDGET = 10
const REPLAY_JUMP_TIME_BUDGET_MS = 5000

interface LoadUntilTimestampOptions {
    initialData: ReplayData | undefined
    targetTs: string
    hasNextPage: boolean | undefined
    fetchNextPage: () => Promise<{ data?: ReplayData, hasNextPage?: boolean }>
    maxPages?: number
    maxElapsedMs?: number
    now?: () => number
}

interface LoadUntilTimestampResult {
    status: 'found' | 'exhausted' | 'unavailable'
    data: ReplayData | undefined
    pagesFetched: number
}

/**
 * Load a bounded number of replay pages while looking for a timeline target.
 * A later invocation can continue from pages cached by the query client.
 */
export const loadUntilTimestamp = async ({
    initialData,
    targetTs,
    hasNextPage,
    fetchNextPage,
    maxPages = REPLAY_JUMP_PAGE_BUDGET,
    maxElapsedMs = REPLAY_JUMP_TIME_BUDGET_MS,
    now = Date.now,
}: LoadUntilTimestampOptions): Promise<LoadUntilTimestampResult> => {
    if (initialData && reachesTimestamp(initialData.pages, targetTs)) {
        return { status: 'found', data: initialData, pagesFetched: 0 }
    }
    if (!initialData || !hasNextPage) {
        return { status: 'unavailable', data: initialData, pagesFetched: 0 }
    }

    const startedAt = now()
    let current: ReplayData | undefined = initialData
    let canFetch: boolean = hasNextPage
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

export const useStreamReplayController = (streamId: number) => {
    const [chatterId, setChatterId] = useState<number | undefined>(undefined)
    const [textQuery, setTextQuery] = useState<string | undefined>(undefined)
    const [subOnly, setSubOnly] = useState(false)
    const [jumpToTs, setJumpToTs] = useState<JumpTarget | null>(null)
    const [jumpFailure, setJumpFailure] = useState<UiFailure | null>(null)
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
        () => data?.pages.flatMap((page: StreamMessagesPage) => page.messages) ?? [],
        [data],
    )

    const handleLoadMore = useCallback(() => {
        if (hasNextPage && !isFetchingNextPage) fetchNextPage()
    }, [hasNextPage, isFetchingNextPage, fetchNextPage])

    const handleJump = useCallback(async (targetTs: string) => {
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
