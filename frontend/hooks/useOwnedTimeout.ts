import { useCallback, useEffect, useRef } from 'react'

/** Schedule one replaceable timeout and guarantee it is cleared on unmount. */
export const useOwnedTimeout = () => {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

    const cancel = useCallback(() => {
        if (timerRef.current !== null) {
            clearTimeout(timerRef.current)
            timerRef.current = null
        }
    }, [])

    useEffect(() => cancel, [cancel])

    const schedule = useCallback((callback: () => void, delayMs: number) => {
        cancel()
        timerRef.current = setTimeout(() => {
            timerRef.current = null
            callback()
        }, delayMs)
    }, [cancel])

    return { schedule, cancel }
}
