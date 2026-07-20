import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Copy text to the clipboard with a timed "Copied" label reset. Owns the three
 * things every copy button was hand-rolling: the `copied` flag, the reset
 * timeout (cleared on unmount so it can't set state on a dead component), and
 * the clipboard-write failure mode — a rejected write (denied permission,
 * insecure context) leaves the label unchanged instead of throwing or
 * pretending it copied.
 */
export const useCopyToClipboard = (resetAfterMs = 2000) => {
    const [copied, setCopied] = useState(false)
    const timerRef = useRef<number | null>(null)

    useEffect(() => () => {
        if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    }, [])

    const copy = useCallback(async (text: string) => {
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            if (timerRef.current !== null) window.clearTimeout(timerRef.current)
            timerRef.current = window.setTimeout(() => setCopied(false), resetAfterMs)
        } catch {
            // Copy is best-effort; a denied/unsupported clipboard leaves the
            // label unchanged rather than pretending it copied.
            setCopied(false)
        }
    }, [resetAfterMs])

    return { copied, copy }
}
