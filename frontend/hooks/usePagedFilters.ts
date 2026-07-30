import { useCallback, useRef, useState } from 'react'

/**
 * Single owner of the paged-filter state machine shared by list controllers:
 * a page index plus a filters object, with the invariant that ANY filter
 * change snaps back to page 0 (a filtered result set has a new page space).
 *
 * Controllers compose domain-specific state (modals, review failures, date
 * validation) around this primitive; the invariant itself is enforced — and
 * directly renderHook-testable — in exactly one place.
 */
export const usePagedFilters = <F extends object>(defaultFilters: F) => {
    // Defaults are captured at mount (ref) so resetFilters restores the original
    // shape even if a caller passes a fresh object literal on every render.
    const defaults = useRef(defaultFilters)
    const [pageIndex, setPageIndex] = useState(0)
    const [filters, setFilters] = useState(defaultFilters)

    const setFilter = useCallback(<K extends keyof F>(key: K, value: F[K]) => {
        setFilters(current => ({ ...current, [key]: value }))
        setPageIndex(0)
    }, [])

    const resetFilters = useCallback(() => {
        setFilters(defaults.current)
        setPageIndex(0)
    }, [])

    /** Step back one page (floored at 0) — e.g. after deleting a page's last row. */
    const retreatPage = useCallback(() => {
        setPageIndex(current => Math.max(current - 1, 0))
    }, [])

    return {
        pageIndex, setPageIndex, filters, setFilter, resetFilters, retreatPage,
    }
}
