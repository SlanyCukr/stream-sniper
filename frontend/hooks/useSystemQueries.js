import {
    useMutation, useQuery, useQueryClient,
} from '@tanstack/react-query'
import {
    flushCache,
    retrieveCacheStats,
    retrieveDetailedHealth,
    retrieveMetrics,
} from '@/lib/api'

/** Query-key factory for system telemetry. */
export const systemKeys = {
    all: [
        'system',
    ],
    detailedHealth: () => [
        ...systemKeys.all,
        'detailed-health',
    ],
    metrics: () => [
        ...systemKeys.all,
        'metrics',
    ],
    cacheStats: () => [
        ...systemKeys.all,
        'cache-stats',
    ],
}

/** Fetch detailed application and dependency health. */
export const useDetailedHealth = (options = {}) => useQuery({
    queryKey: systemKeys.detailedHealth(),
    queryFn: async () => {
        const { data } = await retrieveDetailedHealth()
        return data
    },
    ...options,
})

/** Fetch request and rate-limiting metrics. */
export const useSystemMetrics = (options = {}) => useQuery({
    queryKey: systemKeys.metrics(),
    queryFn: async () => {
        const { data } = await retrieveMetrics()
        return data
    },
    ...options,
})

/** Fetch cache performance and occupancy statistics. */
export const useCacheStats = (options = {}) => useQuery({
    queryKey: systemKeys.cacheStats(),
    queryFn: async () => {
        const { data } = await retrieveCacheStats()
        return data
    },
    ...options,
})

/** Flush caches and refresh every dependent telemetry query. */
export const useFlushCache = (options = {}) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options

    return useMutation({
        ...mutationOptions,
        mutationFn: flushCache,
        onSuccess: async (...args) => {
            await queryClient.invalidateQueries({ queryKey: systemKeys.all })
            await onSuccess?.(...args)
        },
    })
}
