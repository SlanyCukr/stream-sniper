import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { defineGatedQuery, defineQuery } from '@/hooks/defineQuery'

const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: Infinity } },
    })
    const Wrapper = ({ children }: PropsWithChildren) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    return Wrapper
}

describe('defineQuery', () => {
    it('pipes fetch through map and resolves the mapped value', async () => {
        const useThing = defineQuery({
            key: (id: number) => ['thing', id] as const,
            fetch: async id => ({ raw: id * 2 }),
            map: value => (value as { raw: number }).raw + 1,
        })
        const { result } = renderHook(() => useThing(21), { wrapper: createWrapper() })
        await waitFor(() => expect(result.current.isSuccess).toBe(true))
        expect(result.current.data).toBe(43)
    })

    it('surfaces a mapper throw as the query error', async () => {
        const useThing = defineQuery({
            key: () => ['thing'] as const,
            fetch: async () => ({}),
            map: () => {
                throw new TypeError('malformed payload')
            },
        })
        const { result } = renderHook(() => useThing(undefined), { wrapper: createWrapper() })
        await waitFor(() => expect(result.current.isError).toBe(true))
        expect(result.current.error?.message).toBe('malformed payload')
    })

    it('forwards caller options (enabled: false blocks the fetch)', async () => {
        const fetcher = vi.fn(async () => ({}))
        const useThing = defineQuery({
            key: () => ['thing'] as const,
            fetch: fetcher,
            map: () => 'mapped',
        })
        const { result } = renderHook(() => useThing(undefined, { enabled: false }), {
            wrapper: createWrapper(),
        })
        await new Promise(resolve => setTimeout(resolve, 20))
        expect(fetcher).not.toHaveBeenCalled()
        expect(result.current.fetchStatus).toBe('idle')
    })
})

describe('defineGatedQuery', () => {
    const useGated = defineGatedQuery({
        label: 'gated thing',
        key: (id: number | null) => ['gated', { id }] as const,
        validate: id => (id !== null && id > 0 ? id : null),
        fetch: async id => ({ raw: id }),
        map: value => (value as { raw: number }).raw,
    })

    it('stays disabled (no fetch) while arguments are invalid', async () => {
        const { result } = renderHook(() => useGated(null), { wrapper: createWrapper() })
        await new Promise(resolve => setTimeout(resolve, 20))
        expect(result.current.fetchStatus).toBe('idle')
        expect(result.current.data).toBeUndefined()
    })

    it('fetches with the validated (narrowed) arguments once valid', async () => {
        const { result } = renderHook(() => useGated(7), { wrapper: createWrapper() })
        await waitFor(() => expect(result.current.isSuccess).toBe(true))
        expect(result.current.data).toBe(7)
    })

    it('keeps the raw arguments in the key so gated and fetched states never collide', async () => {
        const queryClient = new QueryClient({
            defaultOptions: { queries: { retry: false, gcTime: Infinity } },
        })
        const Wrapper = ({ children }: PropsWithChildren) => (
            <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
        )
        const gatedRender = renderHook(() => useGated(null), { wrapper: Wrapper })
        const validRender = renderHook(() => useGated(7), { wrapper: Wrapper })
        await waitFor(() => expect(validRender.result.current.isSuccess).toBe(true))

        const keys = queryClient.getQueryCache().getAll().map(query => query.queryKey)
        expect(keys).toContainEqual(['gated', { id: null }])
        expect(keys).toContainEqual(['gated', { id: 7 }])
        expect(gatedRender.result.current.data).toBeUndefined()
        expect(validRender.result.current.data).toBe(7)
    })

    it('throws a TypeError if the fetch path is forced while ungated', async () => {
        const wrapper = createWrapper()
        const { result } = renderHook(() => useGated(null), { wrapper })
        await expect(result.current.refetch({ throwOnError: true })).rejects.toThrow(TypeError)
    })

    it('composes with a caller-supplied enabled (valid args, enabled: false, no fetch)', async () => {
        const fetcher = vi.fn(async (id: number) => ({ raw: id }))
        const useSpied = defineGatedQuery({
            label: 'spied',
            key: (id: number | null) => ['spied', { id }] as const,
            validate: id => (id !== null && id > 0 ? id : null),
            fetch: fetcher,
            map: value => (value as { raw: number }).raw,
        })
        const { result } = renderHook(() => useSpied(7, { enabled: false }), {
            wrapper: createWrapper(),
        })
        await new Promise(resolve => setTimeout(resolve, 20))
        expect(fetcher).not.toHaveBeenCalled()
        expect(result.current.fetchStatus).toBe('idle')
    })
})

describe('polling wrapper convention', () => {
    // Pins the destructured-default pattern used by useSceneLive/useSceneRadar:
    // an explicit `refetchInterval: undefined` (from composed optional options)
    // must fall back to the default interval, not disable polling.
    it('explicit undefined refetchInterval keeps the destructured default', async () => {
        const fetcher = vi.fn(async () => ({}))
        const polledQuery = defineQuery({
            key: () => ['polled'] as const,
            fetch: fetcher,
            map: () => 'ok',
        })
        const usePolledLike = (
            { refetchInterval = 40, ...options }: Parameters<typeof polledQuery>[1] & { refetchInterval?: number } = {},
        ) => polledQuery(undefined, { ...options, refetchInterval })

        renderHook(() => usePolledLike({ refetchInterval: undefined }), {
            wrapper: createWrapper(),
        })
        await waitFor(() => expect(fetcher.mock.calls.length).toBeGreaterThanOrEqual(2), {
            timeout: 2000,
        })
    })
})
