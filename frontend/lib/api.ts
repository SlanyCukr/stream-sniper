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
  subOnly?: boolean,
}) => api.get(`/stream/${streamId}/messages?${qs({
  chatter_id: p.chatterId, q: p.q, after_ts: p.afterTs, after_id: p.afterId, limit: p.limit,
  sub_only: p.subOnly || null,
})}`)

// W3 — stream timeline (buckets + moments + metrics)
export const retrieveStreamTimeline = (streamId: number) => api.get(`/stream/${streamId}/timeline`)
export const retrieveStreamComparison = (streamIds: number[]) => {
  const params = new URLSearchParams()
  streamIds.forEach(id => params.append('stream_ids', String(id)))
  return api.get(`/streams/compare?${params}`)
}

// W4 — creator analytics
export const retrieveCreatorSummary = (creatorId: number) => api.get(`/creator/${creatorId}/summary`)
export const retrieveCreatorTrends = (creatorId: number) => api.get(`/creator/${creatorId}/trends`)
export const retrieveCreatorRegulars = (creatorId: number, p: {
  minStreams?: number, sort?: string, dir?: 'asc' | 'desc', limit?: number,
}) => api.get(`/creator/${creatorId}/regulars?${qs({
    min_streams: p.minStreams, sort: p.sort, dir: p.dir, limit: p.limit,
})}`)
export const retrieveAudienceMovement = (creatorId: number, days = 30) =>
  api.get(`/creator/${creatorId}/audience-movement?${qs({ days })}`)

// W5 — per-stream insights (mentions, emotes, phrases) + creator emotes
export const retrieveStreamMentions = (streamId: number, limit = 20) => api.get(`/stream/${streamId}/mentions?${qs({ limit })}`)
export const retrieveStreamEmotes = (streamId: number, limit = 25) => api.get(`/stream/${streamId}/emotes?${qs({ limit })}`)
export const retrieveStreamPhrases = (streamId: number, limit = 25) => api.get(`/stream/${streamId}/phrases?${qs({ limit })}`)
export const retrieveCreatorEmotes = (creatorId: number, limit = 25) => api.get(`/creator/${creatorId}/emotes?${qs({ limit })}`)

// W6 — community overlap
export const retrieveCommunityOverlap = (limit = 40) => api.get(`/community/overlap?${qs({ limit })}`)
export const retrieveCreatorNeighbors = (creatorId: number, p: {
  metric?: 'regulars' | 'chatters', limit?: number,
} = {}) => api.get(`/community/creator/${creatorId}/neighbors?${qs({ metric: p.metric, limit: p.limit })}`)

// W7 — highlight queue + moment review (review endpoints are admin-only)
export const retrieveMomentsQueue = (p: {
  status?: 'pending' | 'bookmarked' | 'rejected' | 'clipped' | 'published', creatorId?: number, limit?: number, offset?: number,
} = {}) => api.get(`/moments?${qs({
  status: p.status, creator_id: p.creatorId, limit: p.limit, offset: p.offset,
})}`)
export const putMomentReview = (
  streamId: number,
  bucketMinute: string,
  status: 'bookmarked' | 'rejected' | 'clipped' | 'published',
  metadata: { clipUrl?: string | null, note?: string | null } = {},
) => api.put(`/stream/${streamId}/moments/${encodeURIComponent(bucketMinute)}/review`, {
  status,
  clip_url: metadata.clipUrl || null,
  note: metadata.note || null,
})
export const deleteMomentReview = (streamId: number, bucketMinute: string) =>
  api.delete(`/stream/${streamId}/moments/${encodeURIComponent(bucketMinute)}/review`)

// W8 — stream report card + data exports
export const retrieveStreamReport = (streamId: number, lookback?: number) => api.get(`/stream/${streamId}/report?${qs({ lookback })}`)
// Blob downloads: the JWT lives in localStorage and is attached by the request
// interceptor, so exports must go through axios (a plain <a href> has no header).
// timeout: 0 — a full chat log can exceed the instance default of 10s.
export const downloadStreamExport = (streamId: number, format: 'ndjson' | 'csv' = 'ndjson') =>
  api.get(`/stream/${streamId}/export?${qs({ format })}`, { responseType: 'blob', timeout: 0 })
export const downloadStreamInsightCsv = (streamId: number, kind: 'emotes' | 'phrases' | 'mentions') =>
  api.get(`/stream/${streamId}/${kind}?format=csv`, { responseType: 'blob', timeout: 0 })

// W9 — scene expansion (live now, leaderboard, copypasta library)
export const retrieveSceneLive = () => api.get('/scene/live')
export const retrieveSceneLeaderboard = (windowDays: 7 | 30 = 7) => api.get(`/scene/leaderboard?${qs({ window: windowDays })}`)
export const retrieveSceneCopypastas = (p: {
  days?: number, creatorId?: number, sort?: 'usage' | 'spread' | 'recent', limit?: number, offset?: number,
} = {}) => api.get(`/scene/copypastas?${qs({
  days: p.days, creator_id: p.creatorId, sort: p.sort, limit: p.limit, offset: p.offset,
})}`)
export const retrieveCopypastaPropagation = (messageTextId: number, contextSeconds = 90) =>
  api.get(`/scene/copypastas/${messageTextId}?${qs({ context_seconds: contextSeconds })}`)
export const retrieveScenePulse = (p: {
  days?: number, eventType?: string, creatorId?: number, limit?: number, offset?: number,
} = {}) => api.get(`/scene/pulse?${qs({
  days: p.days, event_type: p.eventType, creator_id: p.creatorId, limit: p.limit, offset: p.offset,
})}`)
export const retrieveSceneDigest = (days = 7) => api.get(`/scene/digest?${qs({ days })}`)

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
