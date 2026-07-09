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
