import { api, getJson } from './client'

export interface HealthComponentDto {
  status: string
  response_time_ms?: number | null
  details?: Record<string, unknown> | null
}

export interface DetailedHealthDto {
  status: string
  timestamp: string
  uptime_seconds: number
  version?: string
  system: { memory_usage_percent?: number | null }
  components: Record<string, HealthComponentDto>
}

export interface MetricsDto {
  requests: {
    total_requests: number
    successful_requests: number
    failed_requests: number
    average_response_time_ms: number | null
  }
  cache: {
    hit_rate: number
    total_hits: number
    total_misses: number
    total_operations: number
  }
  rate_limiting: {
    total_requests: number
    rate_limited_requests: number
    rate_limit_percentage: number
  }
}

export interface CacheStatsDto {
  cache_stats: {
    backend: string
    status: string
    stream_sniper_keys: number
  }
  performance_metrics: Record<string, unknown>
  timestamp: string
}

export interface FlushCacheDto {
  message: string
  timestamp: string
}

export const retrieveDetailedHealth = () => getJson<DetailedHealthDto>('/health/detailed')
export const retrieveMetrics = () => getJson<MetricsDto>('/metrics')
export const retrieveCacheStats = () => getJson<CacheStatsDto>('/cache/stats')
export const flushCache = () => api.post<FlushCacheDto>('/cache/flush')
