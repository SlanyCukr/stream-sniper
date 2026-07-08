'use client'

/** Full-screen crosshair loader — "acquiring target". */
const Loader = () => (
    <div
        className="fallback-spinner"
        role="status"
        aria-label="Loading"
    >
        <div className="scope-loader">
            <svg
                viewBox="0 0 64 64"
                aria-hidden="true"
            >
                <circle
                    className="scope-ring"
                    cx="32"
                    cy="32"
                    r="22"
                />
                <circle
                    className="scope-sweep"
                    cx="32"
                    cy="32"
                    r="22"
                />
                <path
                    className="scope-cross"
                    d="M32 2v12M32 50v12M2 32h12M50 32h12"
                />
                <circle
                    className="scope-dot"
                    cx="32"
                    cy="32"
                    r="3"
                />
            </svg>
            <span className="scope-text">Acquiring target…</span>
        </div>
    </div>
)

export default Loader
