import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="empty-state" style={{ minHeight: '100vh' }}>
      <div className="empty-scope" aria-hidden="true" />
      <h1 className="page-title mb-2">404 — Target not found</h1>
      <p className="empty-hint mb-4">
        The page you were tracking has gone dark. It may have been moved or never existed.
      </p>
      <Link href="/" className="btn btn-primary">Back to streams</Link>
    </div>
  )
}
