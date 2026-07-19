import {
    useCallback, useEffect, useRef, useState,
} from 'react'

export interface SearchOption {
    label: string
    value: string | number
}

interface UseAsyncSearchLoaderOptions {
    loadOptions: (query: string) => Promise<SearchOption[]>
    debounceMs: number
    onLoadError?: (error: unknown) => void
}

interface PendingResolution {
    resolve: (options: SearchOption[]) => void
}

/**
 * Owns the debounce and retry state machine used by AsyncSearchSelect.
 */
export const useAsyncSearchLoader = ({
    loadOptions,
    debounceMs,
    onLoadError,
}: UseAsyncSearchLoaderOptions) => {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const pendingRef = useRef<PendingResolution | null>(null)
    const lastQueryRef = useRef('')
    const mountedRef = useRef(true)
    const [loadError, setLoadError] = useState<unknown | null>(null)
    const [retrying, setRetrying] = useState(false)
    const [retryVersion, setRetryVersion] = useState(0)
    const [retryOptions, setRetryOptions] = useState<SearchOption[] | null>(null)

    const runLoad = useCallback(async (inputValue: string) => {
        lastQueryRef.current = inputValue
        if (mountedRef.current) setLoadError(null)
        try {
            const options = await loadOptions(inputValue)
            return options
        } catch (searchError) {
            if (mountedRef.current) {
                setLoadError(searchError)
                onLoadError?.(searchError)
            }
            throw searchError
        }
    }, [
        loadOptions,
        onLoadError,
    ])

    const debouncedLoadOptions = useCallback(
    (inputValue: string) => new Promise<SearchOption[]>((resolve, reject) => {
        if (timerRef.current) {
            clearTimeout(timerRef.current)
            pendingRef.current?.resolve([])
        }
        pendingRef.current = { resolve }
        timerRef.current = setTimeout(() => {
            timerRef.current = null
            pendingRef.current = null
            runLoad(inputValue).then(resolve, reject)
        }, debounceMs)
    }), [
        runLoad,
        debounceMs,
    ])

    useEffect(() => {
        mountedRef.current = true
        return () => {
            mountedRef.current = false
            if (timerRef.current) clearTimeout(timerRef.current)
            timerRef.current = null
            pendingRef.current?.resolve([])
            pendingRef.current = null
        }
    }, [])

    const retryLastSearch = async () => {
        setRetrying(true)
        try {
            const options = await runLoad(lastQueryRef.current)
            if (mountedRef.current) {
                setRetryOptions(options)
                setRetryVersion(version => version + 1)
            }
        } catch (loadError) {
            void loadError
            // runLoad already preserves and reports the retry failure.
        } finally {
            if (mountedRef.current) setRetrying(false)
        }
    }

    return {
        debouncedLoadOptions,
        loadError,
        retrying,
        retryVersion,
        retryOptions,
        retryLastSearch,
    }
}
