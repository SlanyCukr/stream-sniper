import { useQuery } from '@tanstack/react-query'
import { useInvalidatingMutation } from '@/hooks/useInvalidatingMutation'
import {
    flushCache,
    retrieveCacheStats,
    retrieveDetailedHealth,
    retrieveMetrics,
} from '@/lib/api/system'
import {
    requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'

export const mapDetailedHealth = value => {
    const data = requireRecord(value, 'detailed health')
    const system = requireRecord(data.system, 'detailed health.system')
    const components = requireRecord(data.components, 'detailed health.components')
    return {
    status: requireStringField(data, 'status', 'detailed health'),
    timestamp: requireStringField(data, 'timestamp', 'detailed health'),
    uptimeSeconds: requireFiniteNumberField(data, 'uptime_seconds', 'detailed health'),
    version: data.version,
    memoryUsagePercent: system.memory_usage_percent ?? null,
    components: Object.entries(components).map(([name, component]) => ({
        name,
        status: component.status,
        responseTimeMs: component.response_time_ms ?? null,
        details: component.details ?? null,
    })),
    }
}

export const mapSystemMetrics = value => {
    const data = requireRecord(value, 'system metrics')
    const requests = requireRecord(data.requests, 'system metrics.requests')
    const cache = requireRecord(data.cache, 'system metrics.cache')
    const rateLimiting = requireRecord(data.rate_limiting, 'system metrics.rate_limiting')
    return {
        requests: {
            totalRequests: requireFiniteNumberField(requests, 'total_requests', 'system metrics.requests'),
            successfulRequests: requireFiniteNumberField(requests, 'successful_requests', 'system metrics.requests'),
            failedRequests: requireFiniteNumberField(requests, 'failed_requests', 'system metrics.requests'),
            averageResponseTimeMs: requests.average_response_time_ms ?? null,
        },
        cache: {
            hitRate: requireFiniteNumberField(cache, 'hit_rate', 'system metrics.cache'),
            totalHits: requireFiniteNumberField(cache, 'total_hits', 'system metrics.cache'),
            totalMisses: requireFiniteNumberField(cache, 'total_misses', 'system metrics.cache'),
            totalOperations: requireFiniteNumberField(cache, 'total_operations', 'system metrics.cache'),
        },
        rateLimiting: {
            totalRequests: requireFiniteNumberField(rateLimiting, 'total_requests', 'system metrics.rate_limiting'),
            rateLimitedRequests: requireFiniteNumberField(
                rateLimiting,
                'rate_limited_requests',
                'system metrics.rate_limiting',
            ),
            rateLimitPercentage: requireFiniteNumberField(
                rateLimiting,
                'rate_limit_percentage',
                'system metrics.rate_limiting',
            ),
        },
    }
}

export const mapCacheStats = value => {
    const data = requireRecord(value, 'cache stats')
    const cache = requireRecord(data.cache_stats, 'cache stats.cache_stats')
    return {
        backend: requireStringField(cache, 'backend', 'cache stats.cache_stats'),
        status: requireStringField(cache, 'status', 'cache stats.cache_stats'),
        streamSniperKeys: requireFiniteNumberField(cache, 'stream_sniper_keys', 'cache stats.cache_stats'),
    }
}

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

export const useDetailedHealth = (options = {}) => useQuery({
    ...options,
    queryKey: systemKeys.detailedHealth(),
    queryFn: async () => {
        const { data } = await retrieveDetailedHealth()
        return mapDetailedHealth(data)
    },
})

export const useSystemMetrics = (options = {}) => useQuery({
    ...options,
    queryKey: systemKeys.metrics(),
    queryFn: async () => {
        const { data } = await retrieveMetrics()
        return mapSystemMetrics(data)
    },
})

export const useCacheStats = (options = {}) => useQuery({
    ...options,
    queryKey: systemKeys.cacheStats(),
    queryFn: async () => {
        const { data } = await retrieveCacheStats()
        return mapCacheStats(data)
    },
})

/** @type {import('@tanstack/react-query').MutationFunction<import('@/lib/api/system').FlushCacheDto, void>} */
const flushCacheMutation = async () => (await flushCache()).data

export const useFlushCache = (options = {}) => {
    return useInvalidatingMutation(
        flushCacheMutation,
        systemKeys.all,
        options,
    )
}
