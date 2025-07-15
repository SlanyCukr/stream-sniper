import { Suspense } from 'react'
import './assets/scss/style.scss'
import App from './App'
import reportWebVitals from './reportWebVitals'
import { HashRouter } from 'react-router-dom'
import Loader from './layouts/loader/Loader'
import { createRoot } from 'react-dom/client'
import {
    QueryClient,
    QueryClientProvider,
} from '@tanstack/react-query'

// Create a client
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            // Stale time: 5 minutes (data is considered fresh for 5 minutes)
            staleTime: 1000 * 60 * 5,
            // Cache time: 10 minutes (data stays in cache for 10 minutes when not in use)
            gcTime: 1000 * 60 * 10,
            // Retry on failure
            retry: 2,
            // Retry delay
            retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
            // Refetch on window focus
            refetchOnWindowFocus: false,
        },
    },
})

const container = document.getElementById('root')
const root = createRoot(container)

root.render(
    <QueryClientProvider client={queryClient}>
        <Suspense fallback={<Loader />}>
            <HashRouter>
                <App />
            </HashRouter>
        </Suspense>
    </QueryClientProvider>,
)

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals()
