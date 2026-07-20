import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { useInvalidatingMutation } from '@/hooks/useInvalidatingMutation'
import {
    flushCache,
    retrieveCacheStats,
    retrieveDetailedHealth,
    retrieveMetrics,
    type FlushCacheDto,
    type HealthComponentDto,
} from '@/lib/api/system'
import {
    requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'

export interface DetailedHealthComponent {
    name: string
    status: string
    responseTimeMs: number | null
    details: Record<string, unknown> | null
}

export interface DetailedHealth {
    status: string
    timestamp: string
    uptimeSeconds: number
    version: string | undefined
    memoryUsagePercent: number | null
    components: DetailedHealthComponent[]
}

export interface SystemMetrics {
    requests: {
        totalRequests: number
        successfulRequests: number
        failedRequests: number
        averageResponseTimeMs: number | null
    }
    cache: {
        hitRate: number
        totalHits: number
        totalMisses: number
        totalOperations: number
    }
    rateLimiting: {
        totalRequests: number
        rateLimitedRequests: number
        rateLimitPercentage: number
    }
}

export interface CacheStats {
    backend: string
    status: string
    streamSniperKeys: number
}

// queryKey/queryFn stay accepted-but-untyped: the hooks below always overwrite
// them with their own key/fetcher (matching runtime behavior), so a caller
// passing either does not influence what actually runs.
type QueryOptions<T> = Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, 'queryKey' | 'queryFn'> & {
    queryKey?: unknown
    queryFn?: unknown
}

export const mapDetailedHealth = (value: unknown): DetailedHealth => {
    const data = requireRecord(value, 'detailed health')
    const system = requireRecord(data.system, 'detailed health.system')
    const components = requireRecord(data.components, 'detailed health.components')
    return {
    status: requireStringField(data, 'status', 'detailed health'),
    timestamp: requireStringField(data, 'timestamp', 'detailed health'),
    uptimeSeconds: requireFiniteNumberField(data, 'uptime_seconds', 'detailed health'),
    version: data.version as string | undefined, // optional field, not runtime-validated (matches DetailedHealthDto.version)
    memoryUsagePercent: (system.memory_usage_percent as number | null | undefined) ?? null,
    components: Object.entries(components).map(([name, component]) => {
        const item = component as HealthComponentDto // per-entry shape trusted, not runtime-validated (matches original traversal)
        return {
            name,
            status: item.status,
            responseTimeMs: item.response_time_ms ?? null,
            details: item.details ?? null,
        }
    }),
    }
}

export const mapSystemMetrics = (value: unknown): SystemMetrics => {
    const data = requireRecord(value, 'system metrics')
    const requests = requireRecord(data.requests, 'system metrics.requests')
    const cache = requireRecord(data.cache, 'system metrics.cache')
    const rateLimiting = requireRecord(data.rate_limiting, 'system metrics.rate_limiting')
    return {
        requests: {
            totalRequests: requireFiniteNumberField(requests, 'total_requests', 'system metrics.requests'),
            successfulRequests: requireFiniteNumberField(requests, 'successful_requests', 'system metrics.requests'),
            failedRequests: requireFiniteNumberField(requests, 'failed_requests', 'system metrics.requests'),
            averageResponseTimeMs: (requests.average_response_time_ms as number | null | undefined) ?? null,
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

export const mapCacheStats = (value: unknown): CacheStats => {
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

export const useDetailedHealth = (options: QueryOptions<DetailedHealth> = {}) => useQuery({
    ...options,
    queryKey: systemKeys.detailedHealth(),
    queryFn: async () => {
        const data = await retrieveDetailedHealth()
        return mapDetailedHealth(data)
    },
})

export const useSystemMetrics = (options: QueryOptions<SystemMetrics> = {}) => useQuery({
    ...options,
    queryKey: systemKeys.metrics(),
    queryFn: async () => {
        const data = await retrieveMetrics()
        return mapSystemMetrics(data)
    },
})

export const useCacheStats = (options: QueryOptions<CacheStats> = {}) => useQuery({
    ...options,
    queryKey: systemKeys.cacheStats(),
    queryFn: async () => {
        const data = await retrieveCacheStats()
        return mapCacheStats(data)
    },
})

const flushCacheMutation = async (): Promise<FlushCacheDto> => (await flushCache()).data

export const useFlushCache = (options = {}) => {
    return useInvalidatingMutation(
        flushCacheMutation,
        systemKeys.all,
        options,
    )
}
