import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { usePagedFilters } from '@/hooks/usePagedFilters'

describe('usePagedFilters', () => {
    it('any filter change snaps back to page 0, including object-valued fields', () => {
        const { result } = renderHook(() => usePagedFilters<{
            status: string
            selectedCreator: { value: number } | null
        }>({ status: '', selectedCreator: null }))
        act(() => result.current.setPageIndex(3))
        expect(result.current.pageIndex).toBe(3)

        act(() => result.current.setFilter('status', 'done'))
        expect(result.current.pageIndex).toBe(0)

        act(() => result.current.setPageIndex(2))
        act(() => result.current.setFilter('selectedCreator', { value: 7 }))
        expect(result.current.pageIndex).toBe(0)
        expect(result.current.filters).toEqual({ status: 'done', selectedCreator: { value: 7 } })
    })

    it('reset restores the defaults frozen at mount, not later prop values', () => {
        const { result, rerender } = renderHook(
            ({ defaults }) => usePagedFilters(defaults),
            { initialProps: { defaults: { status: '' } } },
        )
        act(() => {
            result.current.setFilter('status', 'failed')
            result.current.setPageIndex(2)
        })
        // A caller re-rendering with a different object must not change what
        // reset restores — defaults are frozen at mount.
        rerender({ defaults: { status: 'changed-later' } })
        act(() => result.current.resetFilters())
        expect(result.current.filters).toEqual({ status: '' })
        expect(result.current.pageIndex).toBe(0)
    })

    it('retreatPage steps back exactly one page and floors at 0', () => {
        const { result } = renderHook(() => usePagedFilters({}))
        act(() => result.current.setPageIndex(3))
        act(() => result.current.retreatPage())
        expect(result.current.pageIndex).toBe(2)
        act(() => result.current.setPageIndex(0))
        act(() => result.current.retreatPage())
        expect(result.current.pageIndex).toBe(0)
    })

    it('setFilter identity is stable across renders (safe for memo deps)', () => {
        const { result, rerender } = renderHook(() => usePagedFilters({ q: '' }))
        const first = result.current.setFilter
        act(() => result.current.setFilter('q', 'x'))
        rerender()
        expect(result.current.setFilter).toBe(first)
    })
})
