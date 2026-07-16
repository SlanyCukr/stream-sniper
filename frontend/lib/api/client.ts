import axios, { type AxiosInstance } from 'axios'

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

export function installUnauthorizedInterceptor(onUnauthorized: () => void) {
  const interceptorId = api.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      if (axios.isAxiosError(error)
        && error.response?.status === 401
        && typeof window !== 'undefined') {
        onUnauthorized()
      }
      return Promise.reject(error)
    },
  )

  return () => api.interceptors.response.eject(interceptorId)
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>

export function buildQuery(params: QueryParams) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  return searchParams
}

