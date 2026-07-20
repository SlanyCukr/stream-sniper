import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'

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

type QueryParams = Record<string, string | number | boolean | null | undefined>

export function buildQuery(params: QueryParams) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  return searchParams
}

/**
 * GET a JSON endpoint and unwrap `response.data`, the shape nearly every
 * adapter in lib/api/*.ts wants. Pass `params` to append `?${buildQuery(...)}`
 * (matching the exact URL a call site would have built by hand, including a
 * bare trailing `?` when every param is empty) — omit it entirely for bare
 * paths with no query string at all. `config` is for the rare GET that needs
 * e.g. a custom timeout; sites needing the raw AxiosResponse (headers, Blob
 * responseType) should keep calling `api.get` directly instead.
 */
export const getJson = async <T>(
  path: string,
  params?: QueryParams,
  config?: AxiosRequestConfig,
): Promise<T> => {
  const url = params ? `${path}?${buildQuery(params)}` : path
  // Only forward `config` when the caller actually passed one — an explicit
  // `undefined` second argument is a different (and test-visible) call shape
  // than omitting it outright.
  const response = config ? await api.get<T>(url, config) : await api.get<T>(url)
  return response.data
}

