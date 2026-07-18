'use client'

export default function GlobalError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <html lang="en">
      <body className="dark">
        <div className="container mt-5">
          <div className="alert alert-danger" role="alert">
            <h4 className="alert-heading">Something went wrong</h4>
            <p>The app hit an unexpected problem. Try again, or reload the page if it keeps happening.</p>
            <button className="btn btn-outline-danger" onClick={() => reset()}>Try again</button>
          </div>
        </div>
      </body>
    </html>
  )
}
