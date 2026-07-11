import axios, { AxiosInstance } from 'axios'

let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn
}

export const api: AxiosInstance = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('token')
      onUnauthorized()
    }
    return Promise.reject(error)
  },
)

// Query-string helper: drop null/''/undefined, stringify the rest (keys already snake_case).
type QueryParams = Record<string, string | number | boolean | null | undefined>

const qs = (params: QueryParams) => {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  return searchParams
}

// Data endpoints (baseURL '/api' already applied; paths are backend-relative after /api strip)
export const retrieveMessages = (chatterId: string | number, offset = 0, limit = 50) => api.get(`/chatter/${chatterId}/messages?offset=${offset}&limit=${limit}`)
export const retrieveChatterId = (nick: string) => api.get(`/chatter/${nick}/chatter_id`)
export const retrieveChatterSearch = (q: string, limit = 10) => api.get(`/chatters/search?q=${encodeURIComponent(q)}&limit=${limit}`)
export const retrieveTwitchChannelSearch = (q: string, limit = 8) => api.get(`/admin/tracking/twitch-search?q=${encodeURIComponent(q)}&limit=${limit}`)
export const retrieveChattersOnStream = (streamId: string | number) => api.get(`/stream/${streamId}/chatters`)

// W1 — replaces the old positional retrieveStreams
export const retrieveStreams = (p: {
  creatorId?: number, sort?: string, dir?: 'asc' | 'desc', title?: string,
  dateFrom?: string, dateTo?: string, minMessages?: number, offset?: number,
}) => api.get(`/streams?${qs({
  creator_id: p.creatorId, sort: p.sort, dir: p.dir, title: p.title,
  date_from: p.dateFrom, date_to: p.dateTo, min_messages: p.minMessages, offset: p.offset,
})}`)

// W2 — chronological keyset chat replay for a stream
export const retrieveStreamMessages = (streamId: number, p: {
  chatterId?: number, q?: string, afterTs?: string, afterId?: number, limit?: number,
}) => api.get(`/stream/${streamId}/messages?${qs({
  chatter_id: p.chatterId, q: p.q, after_ts: p.afterTs, after_id: p.afterId, limit: p.limit,
})}`)

// W3 — stream timeline (buckets + moments + metrics)
export const retrieveStreamTimeline = (streamId: number) => api.get(`/stream/${streamId}/timeline`)

// W4 — creator analytics
export const retrieveCreatorTrends = (creatorId: number) => api.get(`/creator/${creatorId}/trends`)
export const retrieveCreatorRegulars = (creatorId: number, p: {
  minStreams?: number, sort?: string, dir?: 'asc' | 'desc', limit?: number,
}) => api.get(`/creator/${creatorId}/regulars?${qs({
  min_streams: p.minStreams, sort: p.sort, dir: p.dir, limit: p.limit,
})}`)

export const retrieveStreamComprehensive = (streamId: string | number) => api.get(`/stream/${streamId}`)
export const retrieveAllCreators = () => api.get('/creators')
export const retrieveChatterStreamActivity = (chatterId: string | number) => api.get(`/chatter/${chatterId}/stream-activity`)

type ApiErrorResponse = {
  detail?: unknown
}

/** Convert Axios and native errors to a safe UI message. */
export const getApiErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    const detail = error.response?.data?.detail
    return typeof detail === 'string' ? detail : error.message || fallback
  }
  return error instanceof Error ? error.message || fallback : fallback
}

// Tracking administration endpoints
type TrackingListParams = Record<string, string | number | boolean | null | undefined>

const trackingParams = (params: TrackingListParams) => {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  return searchParams
}

export const retrieveTrackingStats = () => api.get('/admin/tracking/stats')
export const retrieveTrackedStreamers = (params: TrackingListParams = {}) => api.get(`/admin/tracking/streamers?${trackingParams(params)}`)
export const createTrackedStreamer = (streamer: Record<string, unknown>) => api.post('/admin/tracking/streamers', streamer)
export const updateTrackedStreamer = (streamerId: string | number, changes: Record<string, unknown>) => api.put(`/admin/tracking/streamers/${streamerId}`, changes)
export const deleteTrackedStreamer = (streamerId: string | number) => api.delete(`/admin/tracking/streamers/${streamerId}`)
export const retrieveProcessingJobs = (params: TrackingListParams = {}) => api.get(`/admin/tracking/jobs?${trackingParams(params)}`)

// User administration endpoints
export const retrieveAdminSystemStats = () => api.get('/auth/admin/stats')
export const retrieveUsers = (params: TrackingListParams = {}) => api.get(`/auth/users?${trackingParams(params)}`)
export const createAdminUser = (user: Record<string, unknown>) => api.post('/auth/admin/users', user)
export const updateUser = (userId: string | number, changes: Record<string, unknown>) => api.put(`/auth/users/${userId}`, changes)
export const updateUserRole = (userId: string | number, role: string) => api.put(`/auth/users/${userId}/role?new_role=${encodeURIComponent(role)}`)
export const setUserActive = (userId: string | number, isActive: boolean) => api.put(`/auth/users/${userId}/${isActive ? 'activate' : 'deactivate'}`)
export const deleteUser = (userId: string | number) => api.delete(`/auth/users/${userId}`)

// System telemetry endpoints
export const retrieveDetailedHealth = () => api.get('/health/detailed')
export const retrieveMetrics = () => api.get('/metrics')
export const retrieveCacheStats = () => api.get('/cache/stats')
export const flushCache = () => api.post('/cache/flush')
