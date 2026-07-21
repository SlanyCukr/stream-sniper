'use client'
import {
    Card, Badge,
} from 'react-bootstrap'
import type { NormalizedApiError } from '@/utils/errorUtils'

type ErrorInfo = NormalizedApiError & { timestamp: string }

interface ErrorDetailsProps {
    error: unknown
    errorInfo: ErrorInfo
}

const asRecord = (value: unknown): Record<string, unknown> | null => (
    typeof value === 'object' && value !== null ? value as Record<string, unknown> : null
)

const diagnosticDetails = (error: unknown) => {
    const source = asRecord(error)
    const config = asRecord(asRecord(source?.response)?.config)
    return {
        url: typeof config?.url === 'string' ? config.url : null,
        method: typeof config?.method === 'string' ? config.method : null,
        stack: typeof source?.stack === 'string' ? source.stack : null,
    }
}

const ErrorDetails = ({
    error, errorInfo,
}: ErrorDetailsProps) => {
    const diagnostics = diagnosticDetails(error)
    return (
      <Card className="mt-3 border-secondary">
        <Card.Header className="py-2">
            <small className="text-muted">Technical Details</small>
        </Card.Header>
        <Card.Body className="py-2">
            <dl className="row mb-0">
                <dt className="col-3">Error Type:</dt>
                <dd className="col-9">
                    <Badge bg="secondary">{errorInfo.type}</Badge>
                </dd>

                {errorInfo.status && (
                    <>
                        <dt className="col-3">Status Code:</dt>
                        <dd className="col-9">{errorInfo.status}</dd>
                    </>
                )}

                {diagnostics.url && (
                    <>
                        <dt className="col-3">URL:</dt>
                        <dd className="col-9">
                            <code className="small">{diagnostics.url}</code>
                        </dd>
                    </>
                )}

                {diagnostics.method && (
                    <>
                        <dt className="col-3">Method:</dt>
                        <dd className="col-9">
                            <Badge bg="info">{diagnostics.method.toUpperCase()}</Badge>
                        </dd>
                    </>
                )}

                <dt className="col-3">Retryable:</dt>
                <dd className="col-9">
                    <Badge bg={errorInfo.retryable ? 'success' : 'danger'}>
                        {errorInfo.retryable ? 'Yes' : 'No'}
                    </Badge>
                </dd>
            </dl>

            {diagnostics.stack && (
                <details className="mt-2">
                    <summary className="btn btn-link p-0 small">Stack Trace</summary>
                    <pre className="mt-2 p-2 bg-light border rounded small">
                        {diagnostics.stack}
                    </pre>
                </details>
            )}
        </Card.Body>
      </Card>
    )
}

export default ErrorDetails
