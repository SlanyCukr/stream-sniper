import type { UseQueryResult } from '@tanstack/react-query'
import ErrorAlert from '@/components/common/error/ErrorAlert'

interface CreatorLoadErrorProps<T> {
    query: UseQueryResult<T, Error>
}

const CreatorLoadError = <T,>({ query }: CreatorLoadErrorProps<T>) => (
    query.error ? (
        <ErrorAlert
            error={query.error}
            title="Failed to load creators"
            onRetry={query.refetch}
        />
    ) : null
)

export default CreatorLoadError
