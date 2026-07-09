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

// Data endpoints (baseURL '/api' already applied; paths are backend-relative after /api strip)
export const retrieveMessages = (chatterId: string | number, offset = 0, limit = 50) => api.get(`/chatter/${chatterId}/messages?offset=${offset}&limit=${limit}`)
export const retrieveChatterId = (nick: string) => api.get(`/chatter/${nick}/chatter_id`)
export const retrieveChatterSearch = (q: string, limit = 10) => api.get(`/chatters/search?q=${encodeURIComponent(q)}&limit=${limit}`)
export const retrieveTwitchChannelSearch = (q: string, limit = 8) => api.get(`/admin/tracking/twitch-search?q=${encodeURIComponent(q)}&limit=${limit}`)
export const retrieveChattersOnStream = (streamId: string | number) => api.get(`/stream/${streamId}/chatters`)
export const retrieveStreams = (creatorId: string | number, offset: number) => api.get(`/streams?creator_id=${creatorId}&offset=${offset}`)
export const retrieveStreamComprehensive = (streamId: string | number) => api.get(`/stream/${streamId}`)
export const retrieveChatterOnStreamMessages = (streamId: string | number, chatterId: string | number) => api.get(`/stream/${streamId}/chatter/${chatterId}/messages`)
export const retrieveAllCreators = () => api.get('/creators')
export const retrieveCreatorTopChatters = (creatorId: string | number, limit: number) => api.get(`/creator/${creatorId}/top-chatters?limit=${limit}`)
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
