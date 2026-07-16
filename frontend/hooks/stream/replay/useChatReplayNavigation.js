import {
    useCallback, useEffect, useRef, useState,
} from 'react'

export const useChatReplayNavigation = ({
    messages,
    jumpToTs,
    hasMore,
    isFetchingMore,
    onLoadMore,
}) => {
    const virtuosoRef = useRef(null)
    const handledNonceRef = useRef(null)
    const flashTimerRef = useRef(null)
    const [flashId, setFlashId] = useState(null)

    useEffect(() => {
        const target = jumpToTs && (typeof jumpToTs === 'object' ? jumpToTs.ts : jumpToTs)
        const nonce = jumpToTs && typeof jumpToTs === 'object' ? jumpToTs.nonce : jumpToTs
        if (!target || handledNonceRef.current === nonce) return undefined

        const index = messages.findIndex(message => message.ts >= target)
        if (index < 0) return undefined

        handledNonceRef.current = nonce
        virtuosoRef.current?.scrollToIndex({
            index,
            align: 'start',
        })
        // Synchronized projection of Virtuoso's imperative scroll target.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setFlashId(messages[index].id)
        if (flashTimerRef.current) clearTimeout(flashTimerRef.current)
        flashTimerRef.current = setTimeout(() => {
            setFlashId(null)
            flashTimerRef.current = null
        }, 1600)
        return undefined
    }, [jumpToTs, messages])

    useEffect(() => () => {
        if (flashTimerRef.current) clearTimeout(flashTimerRef.current)
    }, [])

    const handleEndReached = useCallback(() => {
        if (hasMore && !isFetchingMore) onLoadMore?.()
    }, [hasMore, isFetchingMore, onLoadMore])

    return {
        virtuosoRef,
        flashId,
        handleEndReached,
    }
}
