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
