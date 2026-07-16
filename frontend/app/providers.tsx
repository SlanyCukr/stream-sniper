'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { AuthProvider } from '@/contexts/AuthContext'
import { normalizeApiError } from '@/utils/errorUtils'

export const shouldRetryQuery = (failureCount: number, error: unknown) => (
  failureCount < 2 && normalizeApiError(error).retryable
)

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5,
        gcTime: 1000 * 60 * 10,
        retry: shouldRetryQuery,
        retryDelay: (i: number) => Math.min(1000 * 2 ** i, 30000),
        refetchOnWindowFocus: false,
      },
    },
  }))
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  )
}
