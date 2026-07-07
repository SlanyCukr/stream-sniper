'use client'

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="container mt-5">
      <div className="alert alert-danger" role="alert">
        <h4 className="alert-heading">Something went wrong</h4>
        <p>{error.message || 'An unexpected error occurred.'}</p>
        <button className="btn btn-outline-danger" onClick={() => reset()}>Try again</button>
      </div>
    </div>
  )
}
