import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="container mt-5 text-center">
      <h1 className="display-4">404</h1>
      <p className="text-muted">This page could not be found.</p>
      <Link href="/" className="btn btn-primary">Back to streams</Link>
    </div>
  )
}
