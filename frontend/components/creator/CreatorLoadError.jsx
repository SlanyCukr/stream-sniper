import ErrorAlert from '@/components/common/error/ErrorAlert'

const CreatorLoadError = ({ query }) => (
    query.error ? (
        <ErrorAlert
            error={query.error}
            title="Failed to load creators"
            onRetry={query.refetch}
            showDetails={process.env.NODE_ENV === 'development'}
        />
    ) : null
)

export default CreatorLoadError
